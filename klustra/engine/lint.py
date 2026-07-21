from __future__ import annotations

import re
from collections import Counter
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from klustra.core.page import Page
from klustra.linking import resolve_links

LintSeverity = Literal["warning", "error"]

_CITATION_RE = re.compile(r"\^\[.+?\]")
_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


class LintConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    promote_to_error: list[str] = Field(default_factory=list)


class LintFinding(BaseModel):
    model_config = ConfigDict(frozen=True)

    entity_id: str
    category: str
    message: str
    severity: LintSeverity


def lint_pages(
    pages: list[Page],
    bodies: dict[str, str],
    valid_ids: set[str] | None = None,
    config: LintConfig | None = None,
) -> list[LintFinding]:
    """Run quality checks on pages (SPEC §5.1). Warnings by default."""
    cfg = config or LintConfig()
    ids = valid_ids if valid_ids is not None else {p.entity_id for p in pages}
    findings: list[LintFinding] = []

    children_set = _all_children(pages)
    title_counts = Counter(p.title for p in pages)

    for page in pages:
        body = bodies.get(page.entity_id, "")
        findings.extend(_check_orphan(page, children_set))
        findings.extend(_check_stub(page, body))
        findings.extend(_check_missing_citation(page, body))
        findings.extend(_check_broken_wikilinks(page, body, ids))
        findings.extend(_check_self_link(page, body))
        findings.extend(_check_duplicate_title(page, title_counts))

    return [_apply_severity(f, cfg) for f in findings]


def _all_children(pages: list[Page]) -> set[str]:
    result: set[str] = set()
    for p in pages:
        result.update(p.children)
    return result


def _check_orphan(page: Page, children_set: set[str]) -> list[LintFinding]:
    if page.type in ("home", "index"):
        return []
    if page.entity_id in children_set:
        return []
    return [
        LintFinding(
            entity_id=page.entity_id,
            category="orphan",
            message="page is not referenced in any parent's children list",
            severity="warning",
        )
    ]


def _check_stub(page: Page, body: str) -> list[LintFinding]:
    if len(body.strip()) < 50:
        return [
            LintFinding(
                entity_id=page.entity_id,
                category="stub",
                message=f"body is too short ({len(body.strip())} chars)",
                severity="warning",
            )
        ]
    return []


def _check_missing_citation(page: Page, body: str) -> list[LintFinding]:
    if page.level != 0:
        return []
    if not body.strip():
        return []
    if _CITATION_RE.search(body):
        return []
    return [
        LintFinding(
            entity_id=page.entity_id,
            category="missing_citation",
            message="level-0 page has no provenance citations (^[source_id:locator])",
            severity="warning",
        )
    ]


def _check_broken_wikilinks(page: Page, body: str, valid_ids: set[str]) -> list[LintFinding]:
    result = resolve_links(body, valid_ids)
    findings: list[LintFinding] = []
    for target in result.unresolved:
        findings.append(
            LintFinding(
                entity_id=page.entity_id,
                category="broken_wikilink",
                message=f"wikilink [[{target.raw}]] does not resolve to any known entity",
                severity="warning",
            )
        )
    return findings


def _check_self_link(page: Page, body: str) -> list[LintFinding]:
    for match in _WIKILINK_RE.finditer(body):
        target = match.group(1).strip()
        if target == page.entity_id:
            return [
                LintFinding(
                    entity_id=page.entity_id,
                    category="self_link",
                    message="page contains a wikilink to itself",
                    severity="warning",
                )
            ]
    return []


def _check_duplicate_title(page: Page, title_counts: Counter[str]) -> list[LintFinding]:
    if title_counts[page.title] > 1:
        return [
            LintFinding(
                entity_id=page.entity_id,
                category="duplicate_title",
                message=f"title {page.title!r} is shared with other pages",
                severity="warning",
            )
        ]
    return []


def _apply_severity(finding: LintFinding, config: LintConfig) -> LintFinding:
    if finding.category in config.promote_to_error and finding.severity == "warning":
        return finding.model_copy(update={"severity": "error"})
    return finding
