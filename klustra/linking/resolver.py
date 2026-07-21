from __future__ import annotations

import re
from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict

_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


class LinkTarget(BaseModel):
    model_config = ConfigDict(frozen=True)

    raw: str
    entity_id: str | None = None


class ResolveResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    body: str
    resolved: list[LinkTarget]
    unresolved: list[LinkTarget]


def resolve_links(
    body_md: str,
    valid_ids: set[str],
    aliases: Mapping[str, str] | None = None,
) -> ResolveResult:
    """Validate all [[...]] refs in body against a closed entity_id set.

    Unresolved links stay in the body unchanged — they become lint findings downstream.
    """
    alias_map = aliases or {}
    resolved: list[LinkTarget] = []
    unresolved: list[LinkTarget] = []

    for match in _WIKILINK_RE.finditer(body_md):
        raw = match.group(1).strip()
        if not raw:
            unresolved.append(LinkTarget(raw=match.group(1)))
            continue

        if raw in valid_ids:
            resolved.append(LinkTarget(raw=raw, entity_id=raw))
        elif raw in alias_map:
            resolved.append(LinkTarget(raw=raw, entity_id=alias_map[raw]))
        else:
            unresolved.append(LinkTarget(raw=raw))

    return ResolveResult(body=body_md, resolved=resolved, unresolved=unresolved)
