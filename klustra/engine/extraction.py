from __future__ import annotations

from typing import Any

from klustra.core.knowledge_unit import KnowledgeUnit
from klustra.engine.models import (
    CONCEPT_CANDIDATES_SCHEMA,
    ConceptCandidate,
    ExtractionResult,
)
from klustra.llm import (
    AccountingSink,
    LLMMessage,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    TokenRecord,
)


def extract_concepts(
    units: list[KnowledgeUnit],
    source_id: str,
    existing_index: list[str],
    provider: LLMProvider,
    model: str,
    sink: AccountingSink,
    max_tokens: int | None = None,
    retry_attempts: int | None = None,
) -> list[ExtractionResult]:
    """Phase 1 extraction: LLM structured output for concept candidates (SPEC §5)."""
    results: list[ExtractionResult] = []

    for unit in units:
        request = _build_request(unit, existing_index, model, max_tokens, retry_attempts, source_id)
        response = provider.call(request)

        sink.record(
            TokenRecord(
                role="extraction",
                model=model,
                tokens_in=response.tokens_in,
                tokens_out=response.tokens_out,
            )
        )

        candidates = _parse_response(response)
        results.append(
            ExtractionResult(
                source_id=source_id,
                unit_id=unit.unit_id,
                candidates=candidates,
            )
        )

    return results


def _build_request(
    unit: KnowledgeUnit,
    existing_index: list[str],
    model: str,
    max_tokens: int | None,
    retry_attempts: int | None = None,
    source_id: str = "",
) -> LLMRequest:
    system_content = (
        "You are an extraction engine. Given a knowledge unit, identify concept candidates.\n"
        "Return structured JSON with a list of candidates.\n"
        "Each candidate has: name, entity_id_proposal (dot-separated lowercase), "
        "summary, is_new (true if not in existing index), related_existing (entity_ids from index)."
    )

    index_str = ", ".join(existing_index) if existing_index else "(empty)"
    user_content = (
        f"## Existing entity index\n{index_str}\n\n"
        f"## Knowledge unit [{unit.kind}]\nLocator: {unit.locator}\n\n{unit.content_md}"
    )

    return LLMRequest(
        messages=[
            LLMMessage(role="system", content=system_content),
            LLMMessage(role="user", content=user_content),
        ],
        model=model,
        max_tokens=max_tokens,
        response_schema=CONCEPT_CANDIDATES_SCHEMA,
        retry_attempts=retry_attempts,
        label=f"extraction:{source_id}:{unit.unit_id}",
    )


def _parse_response(response: LLMResponse) -> list[ConceptCandidate]:
    parsed: dict[str, Any] = response.parsed or {}
    raw_candidates = parsed.get("candidates", [])
    candidates: list[ConceptCandidate] = []
    for raw in raw_candidates:
        candidates.append(ConceptCandidate.model_validate(raw))
    return candidates
