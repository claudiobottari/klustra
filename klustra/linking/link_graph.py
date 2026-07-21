from __future__ import annotations

import re
from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict

_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


class LinkEdge(BaseModel):
    model_config = ConfigDict(frozen=True)

    from_entity: str
    to_entity: str


def extract_links(entity_id: str, body_md: str) -> list[LinkEdge]:
    """Extract directed edges from a single page body. Deterministic, no LLM."""
    edges: list[LinkEdge] = []
    seen: set[str] = set()
    for match in _WIKILINK_RE.finditer(body_md):
        target = match.group(1).strip()
        if target and target not in seen:
            seen.add(target)
            edges.append(LinkEdge(from_entity=entity_id, to_entity=target))
    return edges


def build_link_graph(pages: Iterable[tuple[str, str]]) -> list[LinkEdge]:
    """Build the full link graph from (entity_id, body_md) pairs."""
    edges: list[LinkEdge] = []
    for entity_id, body_md in pages:
        edges.extend(extract_links(entity_id, body_md))
    return edges
