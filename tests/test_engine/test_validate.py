from __future__ import annotations

from datetime import UTC, datetime

from klustra.core.page import Page
from klustra.engine.validate import ValidationFinding, validate_all, validate_page


def _make_page(entity_id: str, page_type: str = "concept") -> Page:
    now = datetime.now(UTC)
    return Page(
        type=page_type,  # type: ignore[arg-type]
        level=0,
        entity_id=entity_id,
        title="Test",
        domain="test",
        confidence=0.9,
        created_at=now,
        updated_at=now,
    )


def test_valid_page_passes() -> None:
    page = _make_page("prod.cable.p-laser-320kv")
    findings = validate_page(page)
    assert findings == []


def test_valid_page_with_dots_and_dashes() -> None:
    page = _make_page("a.b-c.d_e")
    findings = validate_page(page)
    assert findings == []


def test_validate_all_clean() -> None:
    pages = [_make_page("prod.cable.a"), _make_page("prod.cable.b")]
    findings = validate_all(pages)
    assert findings == []


def test_validate_detects_invalid_entity_id() -> None:
    now = datetime.now(UTC)
    page = Page.model_construct(
        type="concept",
        level=0,
        entity_id="INVALID ID!",
        title="Bad",
        domain="test",
        confidence=0.9,
        created_at=now,
        updated_at=now,
        description="",
        aliases=[],
        tags=[],
        sources=[],
        children=[],
        memberships=[],
        cluster_meta=None,
        superseded_by=None,
        schema_version="1.0",
    )
    findings = validate_page(page)
    assert len(findings) == 1
    assert "path-safe" in findings[0].message


def test_validate_all_collects_findings() -> None:
    now = datetime.now(UTC)
    good = _make_page("prod.cable.valid")
    bad = Page.model_construct(
        type="concept",
        level=0,
        entity_id="BAD!",
        title="Bad",
        domain="test",
        confidence=0.9,
        created_at=now,
        updated_at=now,
        description="",
        aliases=[],
        tags=[],
        sources=[],
        children=[],
        memberships=[],
        cluster_meta=None,
        superseded_by=None,
        schema_version="1.0",
    )
    findings = validate_all([good, bad])
    assert len(findings) == 1
    assert findings[0].entity_id == "BAD!"


def test_validate_never_fails_on_broken_links() -> None:
    page = _make_page("prod.cable.good")
    findings = validate_page(page)
    assert findings == []


def test_validate_finding_model() -> None:
    f = ValidationFinding(entity_id="x", message="bad")
    assert f.entity_id == "x"
    assert f.message == "bad"
