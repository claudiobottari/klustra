from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict

from klustra.core.page import Page

_ENTITY_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*(\.[a-z0-9][a-z0-9_-]*)*$")


class ValidationFinding(BaseModel):
    """A single OKF conformance finding (SPEC §5.1). Not an exception."""

    model_config = ConfigDict(frozen=True)

    entity_id: str
    message: str


def validate_page(page: Page) -> list[ValidationFinding]:
    """Check single page OKF §9 conformance.

    Only hard conformance: frontmatter parseable (guaranteed by Pydantic), type non-empty,
    path=identity (entity_id is valid path). Never fails on broken links or missing optional fields.
    """
    findings: list[ValidationFinding] = []

    if not page.type:
        findings.append(
            ValidationFinding(entity_id=page.entity_id, message="type must not be empty")
        )

    if not _ENTITY_ID_RE.match(page.entity_id):
        findings.append(
            ValidationFinding(
                entity_id=page.entity_id,
                message=f"entity_id {page.entity_id!r} is not a valid path-safe identifier",
            )
        )

    return findings


def validate_all(pages: list[Page]) -> list[ValidationFinding]:
    """Validate all pages. Returns empty list on full conformance."""
    findings: list[ValidationFinding] = []
    for page in pages:
        findings.extend(validate_page(page))
    return findings
