"""Incremental hierarchy update — materiality filter + LLM judge (SPEC §6.2)."""

from __future__ import annotations

import math
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from klustra.llm import (
    AccountingSink,
    LLMMessage,
    LLMProvider,
    LLMRequest,
    PromptRegistry,
    TokenRecord,
)

JudgeVerdict = Literal["fits", "regenerate_page", "recluster_subtree"]


class MaterialityResult(BaseModel):
    """Result of materiality pre-filter for one concept."""

    model_config = ConfigDict(frozen=True)

    entity_id: str
    cosine_distance: float = Field(ge=0.0)
    is_material: bool


class JudgeResult(BaseModel):
    """LLM judge verdict for one affected cluster."""

    model_config = ConfigDict(frozen=True)

    cluster_entity_id: str
    verdict: JudgeVerdict
    reason: str


class IncrementalConfig(BaseModel):
    """Configuration for incremental hierarchy updates (SPEC §6.2)."""

    model_config = ConfigDict(frozen=True)

    materiality_threshold: float = Field(default=0.10, ge=0.0, le=1.0)
    drift_threshold_percent: float = Field(default=0.30, ge=0.0, le=1.0)
    judge_model: str = "default"
    judge_retry_attempts: int | None = None


class IncrementalResult(BaseModel):
    """Output of run_incremental()."""

    model_config = ConfigDict(frozen=True)

    skipped: list[str] = Field(default_factory=list)
    judged: list[JudgeResult] = Field(default_factory=list)
    regenerated: list[str] = Field(default_factory=list)
    reclustered: list[str] = Field(default_factory=list)
    triggered_full_rebuild: bool = False


JUDGE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "verdict": {
            "type": "string",
            "enum": ["fits", "regenerate_page", "recluster_subtree"],
        },
        "reason": {"type": "string"},
    },
    "required": ["verdict", "reason"],
}


def cosine_distance(a: list[float], b: list[float]) -> float:
    """Cosine distance between two vectors: 1 - cos(a, b)."""
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 1.0
    similarity = dot / (norm_a * norm_b)
    similarity = max(-1.0, min(1.0, similarity))
    return 1.0 - similarity


def check_materiality(
    entity_id: str,
    old_embedding: list[float],
    new_embedding: list[float],
    threshold: float,
) -> MaterialityResult:
    """Materiality pre-filter: cosine distance >= threshold means material change."""
    dist = cosine_distance(old_embedding, new_embedding)
    return MaterialityResult(
        entity_id=entity_id,
        cosine_distance=dist,
        is_material=dist >= threshold,
    )


def judge_cluster(
    cluster_entity_id: str,
    cluster_summary: str,
    member_titles: list[str],
    delta_description: str,
    provider: LLMProvider,
    sink: AccountingSink,
    model: str,
    prompts: PromptRegistry | None = None,
    retry_attempts: int | None = None,
) -> JudgeResult:
    """LLM judge: decide cluster action after member changes (SPEC §6.2)."""
    registry = prompts or PromptRegistry()

    system_content = registry.render(
        "judge",
        cluster_entity_id=cluster_entity_id,
        cluster_summary=cluster_summary,
        member_titles=member_titles,
        delta_description=delta_description,
    )

    user_content = (
        f"Judge cluster '{cluster_entity_id}' after the following changes:\n"
        f"{delta_description}\n\n"
        "Return your verdict as structured JSON."
    )

    request = LLMRequest(
        messages=[
            LLMMessage(role="system", content=system_content),
            LLMMessage(role="user", content=user_content),
        ],
        model=model,
        response_schema=JUDGE_SCHEMA,
        retry_attempts=retry_attempts,
        label=f"judge:{cluster_entity_id}",
    )
    response = provider.call(request)

    sink.record(
        TokenRecord(
            role="judge",
            model=model,
            tokens_in=response.tokens_in,
            tokens_out=response.tokens_out,
        )
    )

    parsed: dict[str, Any] = response.parsed or {}
    verdict_raw = parsed.get("verdict", "fits")
    if verdict_raw not in ("fits", "regenerate_page", "recluster_subtree"):
        verdict_raw = "fits"
    verdict: JudgeVerdict = verdict_raw
    reason = parsed.get("reason", "")

    return JudgeResult(
        cluster_entity_id=cluster_entity_id,
        verdict=verdict,
        reason=reason,
    )


def should_full_rebuild(
    changed_count: int,
    total_count: int,
    drift_threshold_percent: float,
    force_full: bool = False,
) -> bool:
    """Check if full hierarchy rebuild is needed (SPEC §6.2)."""
    if force_full:
        return True
    if total_count == 0:
        return True
    drift = changed_count / total_count
    return drift >= drift_threshold_percent


def run_incremental(
    changed_ids: list[str],
    removed_ids: list[str],
    added_ids: list[str],
    cluster_membership: dict[str, str],
    cluster_summaries: dict[str, str],
    old_embeddings: dict[str, list[float]],
    new_embeddings: dict[str, list[float]],
    config: IncrementalConfig,
    provider: LLMProvider,
    sink: AccountingSink,
    prompts: PromptRegistry | None = None,
) -> IncrementalResult:
    """Incremental hierarchy update driver (SPEC §6.2).

    1. Materiality pre-filter on changed concepts
    2. Identify affected clusters from material changes + added + removed
    3. LLM judge per affected cluster
    4. Return results for caller to execute
    """
    skipped: list[str] = []
    material_ids: list[str] = []

    # Step 1: materiality pre-filter
    for eid in changed_ids:
        old_emb = old_embeddings.get(eid)
        new_emb = new_embeddings.get(eid)
        if old_emb is None or new_emb is None:
            material_ids.append(eid)
            continue
        result = check_materiality(eid, old_emb, new_emb, config.materiality_threshold)
        if result.is_material:
            material_ids.append(eid)
        else:
            skipped.append(eid)

    # Step 2: identify affected clusters
    affected_clusters: set[str] = set()
    all_delta_ids = material_ids + added_ids + removed_ids

    for eid in all_delta_ids:
        parent = cluster_membership.get(eid)
        if parent is not None:
            affected_clusters.add(parent)

    # Step 3: LLM judge per affected cluster
    judged: list[JudgeResult] = []
    regenerated: list[str] = []
    reclustered: list[str] = []

    for cluster_id in sorted(affected_clusters):
        summary = cluster_summaries.get(cluster_id, "")

        members_in_cluster = [
            eid for eid, parent in cluster_membership.items() if parent == cluster_id
        ]

        delta_parts: list[str] = []
        for eid in all_delta_ids:
            if cluster_membership.get(eid) == cluster_id:
                if eid in added_ids:
                    delta_parts.append(f"Added: {eid}")
                elif eid in removed_ids:
                    delta_parts.append(f"Removed: {eid}")
                else:
                    delta_parts.append(f"Modified: {eid}")
        delta_description = "\n".join(delta_parts) if delta_parts else "Minor modifications"

        judge_result = judge_cluster(
            cluster_entity_id=cluster_id,
            cluster_summary=summary,
            member_titles=members_in_cluster,
            delta_description=delta_description,
            provider=provider,
            sink=sink,
            model=config.judge_model,
            prompts=prompts,
            retry_attempts=config.judge_retry_attempts,
        )
        judged.append(judge_result)

        if judge_result.verdict == "regenerate_page":
            regenerated.append(cluster_id)
        elif judge_result.verdict == "recluster_subtree":
            reclustered.append(cluster_id)

    return IncrementalResult(
        skipped=skipped,
        judged=judged,
        regenerated=regenerated,
        reclustered=reclustered,
        triggered_full_rebuild=False,
    )
