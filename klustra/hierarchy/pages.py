"""Cluster & home page generation — recursive driver (SPEC §6.1)."""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from klustra.core.page import ClusterMeta, Page
from klustra.hierarchy.clustering import ClusterResult, PageInput, cluster_pages
from klustra.hierarchy.embeddings import EmbeddingCache, EmbeddingProvider
from klustra.llm import (
    AccountingSink,
    LLMMessage,
    LLMProvider,
    LLMRequest,
    PromptRegistry,
    TokenRecord,
)

_SLUG_RE = re.compile(r"[^a-z0-9-]")


class HierarchyNode(BaseModel):
    """Input node carrying fields for both clustering and LLM synthesis."""

    model_config = ConfigDict(frozen=True)

    entity_id: str
    content_hash: str
    body_md: str
    title: str
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    level: int = 0


class HierarchyConfig(BaseModel):
    """Configuration for the recursive hierarchy builder."""

    model_config = ConfigDict(frozen=True)

    mode: Literal["hard", "soft"] = "hard"
    min_cluster_size: int = 4
    home_threshold: int = 5
    probability_threshold: float = 0.5
    model: str = "default"
    domain: str = "default"
    retry_attempts: int | None = None


class HierarchyResult(BaseModel):
    """Output of build_hierarchy()."""

    model_config = ConfigDict(frozen=True)

    pages: list[Page]
    bodies: dict[str, str] = Field(default_factory=dict)
    max_level: int


CLUSTER_PAGE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "description": {"type": "string"},
        "body_md": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "entity_id_slug": {"type": "string"},
    },
    "required": ["title", "description", "body_md", "tags", "entity_id_slug"],
}


def _sanitize_slug(raw: str) -> str:
    """Normalize LLM-generated slug to valid entity_id segment."""
    slug = raw.lower().strip().replace(" ", "-")
    slug = _SLUG_RE.sub("", slug)
    return slug[:40] or "cluster"


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def synthesize_cluster_page(
    cluster_id: int,
    members: list[HierarchyNode],
    level: int,
    config: HierarchyConfig,
    provider: LLMProvider,
    sink: AccountingSink,
    run_id: str,
    prompts: PromptRegistry | None = None,
) -> tuple[Page, str]:
    """LLM-synthesize one cluster page from member metadata (SPEC §6.1)."""
    registry = prompts or PromptRegistry()

    member_dicts = [
        {"title": m.title, "description": m.description, "tags": m.tags} for m in members
    ]
    system_content = registry.render(
        "hierarchy",
        domain=config.domain,
        level=level,
        members=member_dicts,
    )

    user_parts = [f"Generate a cluster page for {len(members)} members at level {level}."]
    for m in members:
        user_parts.append(f"- [[{m.entity_id}]]: {m.title}")
    user_content = "\n".join(user_parts)

    request = LLMRequest(
        messages=[
            LLMMessage(role="system", content=system_content),
            LLMMessage(role="user", content=user_content),
        ],
        model=config.model,
        response_schema=CLUSTER_PAGE_SCHEMA,
        retry_attempts=config.retry_attempts,
        label=f"hierarchy:cluster:l{level}:c{cluster_id}",
    )
    response = provider.call(request)

    sink.record(
        TokenRecord(
            role="hierarchy",
            model=config.model,
            tokens_in=response.tokens_in,
            tokens_out=response.tokens_out,
        )
    )

    parsed: dict[str, Any] = response.parsed or {}
    title = parsed.get("title", "Cluster")
    description = parsed.get("description", "")
    body_md = parsed.get("body_md", "")
    tags = parsed.get("tags", [])
    slug = _sanitize_slug(parsed.get("entity_id_slug", f"c{cluster_id}"))

    entity_id = f"{config.domain}.cluster.l{level}.{slug}"
    children = [m.entity_id for m in members]
    now = datetime.now(UTC)

    page = Page(
        type="cluster",
        level=level,
        entity_id=entity_id,
        title=title,
        description=description,
        domain=config.domain,
        tags=tags,
        confidence=0.8,
        children=children,
        cluster_meta=ClusterMeta(
            algo="hdbscan" if config.mode == "hard" else "gmm",
            run_id=run_id,
            cohesion=0.7,
        ),
        created_at=now,
        updated_at=now,
    )
    return page, body_md


def synthesize_home_page(
    top_nodes: list[HierarchyNode],
    level: int,
    config: HierarchyConfig,
    provider: LLMProvider,
    sink: AccountingSink,
    run_id: str,
    prompts: PromptRegistry | None = None,
) -> tuple[Page, str]:
    """Generate the terminal home page for a domain (SPEC §6.1)."""
    registry = prompts or PromptRegistry()

    node_dicts = [
        {"title": n.title, "description": n.description, "tags": n.tags} for n in top_nodes
    ]
    system_content = registry.render(
        "home",
        domain=config.domain,
        top_nodes=node_dicts,
    )

    user_parts = [f"Generate the home page for domain '{config.domain}'."]
    for n in top_nodes:
        user_parts.append(f"- [[{n.entity_id}]]: {n.title}")
    user_content = "\n".join(user_parts)

    request = LLMRequest(
        messages=[
            LLMMessage(role="system", content=system_content),
            LLMMessage(role="user", content=user_content),
        ],
        model=config.model,
        response_schema=CLUSTER_PAGE_SCHEMA,
        retry_attempts=config.retry_attempts,
        label=f"hierarchy:home:l{level}:{config.domain}",
    )
    response = provider.call(request)

    sink.record(
        TokenRecord(
            role="hierarchy",
            model=config.model,
            tokens_in=response.tokens_in,
            tokens_out=response.tokens_out,
        )
    )

    parsed: dict[str, Any] = response.parsed or {}
    title = parsed.get("title", f"{config.domain} Home")
    description = parsed.get("description", "")
    body_md = parsed.get("body_md", "")
    tags = parsed.get("tags", [])

    entity_id = f"{config.domain}.home"
    children = [n.entity_id for n in top_nodes]
    now = datetime.now(UTC)

    page = Page(
        type="home",
        level=level,
        entity_id=entity_id,
        title=title,
        description=description,
        domain=config.domain,
        tags=tags,
        confidence=1.0,
        children=children,
        cluster_meta=ClusterMeta(
            algo="hdbscan" if config.mode == "hard" else "gmm",
            run_id=run_id,
            cohesion=1.0,
        ),
        created_at=now,
        updated_at=now,
    )
    return page, body_md


def build_hierarchy(
    nodes: list[HierarchyNode],
    embedding_provider: EmbeddingProvider,
    llm_provider: LLMProvider,
    config: HierarchyConfig,
    sink: AccountingSink,
    run_id: str,
    cache: EmbeddingCache | None = None,
    prompts: PromptRegistry | None = None,
) -> HierarchyResult:
    """Recursive driver: cluster → generate pages → repeat until home (SPEC §6.1)."""
    all_pages: list[Page] = []
    all_bodies: dict[str, str] = {}

    current_nodes = list(nodes)
    current_level = (nodes[0].level if nodes else 0) + 1

    while True:
        # Stop condition: few enough nodes → generate home
        if len(current_nodes) <= config.home_threshold:
            page, body = synthesize_home_page(
                current_nodes, current_level, config, llm_provider, sink, run_id, prompts
            )
            all_pages.append(page)
            all_bodies[page.entity_id] = body
            break

        # Cluster current nodes
        page_inputs = [
            PageInput(
                entity_id=n.entity_id,
                content_hash=n.content_hash,
                body_md=n.body_md,
            )
            for n in current_nodes
        ]

        cluster_result: ClusterResult = cluster_pages(
            page_inputs,
            embedding_provider,
            mode=config.mode,
            min_cluster_size=config.min_cluster_size,
            probability_threshold=config.probability_threshold,
            cache=cache,
        )

        # Single cluster or no clusters → generate home
        if cluster_result.n_clusters <= 1:
            page, body = synthesize_home_page(
                current_nodes, current_level, config, llm_provider, sink, run_id, prompts
            )
            all_pages.append(page)
            all_bodies[page.entity_id] = body
            break

        # Group nodes by cluster_id
        node_map = {n.entity_id: n for n in current_nodes}
        clusters: dict[int, list[HierarchyNode]] = {}
        outlier_nodes: list[HierarchyNode] = []

        for assignment in cluster_result.assignments:
            if assignment.cluster_id == -1:
                outlier_nodes.append(node_map[assignment.entity_id])
            else:
                clusters.setdefault(assignment.cluster_id, []).append(
                    node_map[assignment.entity_id]
                )

        # Synthesize cluster pages
        next_nodes: list[HierarchyNode] = []
        for cid, members in sorted(clusters.items()):
            page, body = synthesize_cluster_page(
                cid, members, current_level, config, llm_provider, sink, run_id, prompts
            )
            all_pages.append(page)
            all_bodies[page.entity_id] = body

            # Convert cluster page to node for next iteration
            next_nodes.append(
                HierarchyNode(
                    entity_id=page.entity_id,
                    content_hash=_content_hash(body),
                    body_md=body,
                    title=page.title,
                    description=page.description,
                    tags=page.tags,
                    level=current_level,
                )
            )

        # Outliers pass through
        next_nodes.extend(outlier_nodes)

        current_nodes = next_nodes
        current_level += 1

    return HierarchyResult(
        pages=all_pages,
        bodies=all_bodies,
        max_level=current_level,
    )
