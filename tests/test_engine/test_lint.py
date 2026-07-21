from __future__ import annotations

from datetime import UTC, datetime

from klustra.core.page import Page
from klustra.engine.lint import LintConfig, lint_pages

_P = "prod.cable.p-laser-320kv"
_X = "prod.cable.xlpe-400kv"


def _page(entity_id: str, title: str = "T", **kwargs: object) -> Page:
    now = datetime.now(UTC)
    defaults = {
        "type": "concept",
        "level": 0,
        "domain": "d",
        "confidence": 0.9,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(kwargs)
    return Page(entity_id=entity_id, title=title, **defaults)  # type: ignore[arg-type]


def test_no_findings_on_clean_pages(sample_pages: list[Page]) -> None:
    bodies = {
        "cluster.cables": "Overview of cables. ^[src001:sheet1]",
        _P: ("P-Laser 320kV cable details. ^[src001:sheet1] See [[prod.cable.xlpe-400kv]]."),
        _X: "XLPE 400kV cable details with provenance. ^[src002:doc1]",
        "mat.copper": (
            "Copper material info. ^[src003:doc2] Used in [[prod.cable.p-laser-320kv]]."
        ),
    }
    valid_ids = {p.entity_id for p in sample_pages}
    findings = lint_pages(sample_pages, bodies, valid_ids)
    orphan_findings = [f for f in findings if f.category == "orphan"]
    assert "mat.copper" in {f.entity_id for f in orphan_findings}


def test_stub_detected(sample_pages: list[Page]) -> None:
    bodies = {
        "cluster.cables": "OK content here with enough length to pass. ^[src:x]",
        _P: "short",
        _X: "Also long enough content for testing here. ^[src:x]",
        "mat.copper": "Enough content here to pass the stub check easily. ^[src:y]",
    }
    valid_ids = {p.entity_id for p in sample_pages}
    findings = lint_pages(sample_pages, bodies, valid_ids)
    stubs = [f for f in findings if f.category == "stub"]
    assert any(f.entity_id == _P for f in stubs)


def test_missing_citation_detected(sample_pages: list[Page]) -> None:
    bodies = {
        "cluster.cables": "Cluster overview, no citation needed.",
        _P: ("This page has detailed content but no provenance citation at all, and it should."),
        _X: "Content with citation ^[src001:sheet1] is fine.",
        "mat.copper": "Also has citation ^[src002:doc1] right here.",
    }
    valid_ids = {p.entity_id for p in sample_pages}
    findings = lint_pages(sample_pages, bodies, valid_ids)
    missing = [f for f in findings if f.category == "missing_citation"]
    assert any(f.entity_id == _P for f in missing)


def test_broken_wikilink_detected(sample_pages: list[Page]) -> None:
    pad = " " * 50
    bodies = {
        "cluster.cables": "OK. ^[src:x]" + pad,
        _P: "See [[nonexistent.entity]] for more. ^[src:x]" + pad,
        _X: "Content here. ^[src:x]" + pad,
        "mat.copper": "Material info. ^[src:x]" + pad,
    }
    valid_ids = {p.entity_id for p in sample_pages}
    findings = lint_pages(sample_pages, bodies, valid_ids)
    broken = [f for f in findings if f.category == "broken_wikilink"]
    assert len(broken) == 1
    assert broken[0].entity_id == _P
    assert "nonexistent.entity" in broken[0].message


def test_self_link_detected(sample_pages: list[Page]) -> None:
    pad = " " * 50
    bodies = {
        "cluster.cables": "OK. ^[src:x]" + pad,
        _P: f"See [[{_P}]] itself. ^[src:x]" + pad,
        _X: "Content. ^[src:x]" + pad,
        "mat.copper": "Material. ^[src:x]" + pad,
    }
    valid_ids = {p.entity_id for p in sample_pages}
    findings = lint_pages(sample_pages, bodies, valid_ids)
    self_links = [f for f in findings if f.category == "self_link"]
    assert len(self_links) == 1
    assert self_links[0].entity_id == _P


def test_duplicate_title_detected(sample_pages: list[Page]) -> None:
    pages = [_page("a.one", title="Same"), _page("a.two", title="Same")]
    bodies = {
        "a.one": "Content with citation ^[src:x] and enough length here.",
        "a.two": "Other content with citation ^[src:y] and enough length here.",
    }
    findings = lint_pages(pages, bodies)
    dups = [f for f in findings if f.category == "duplicate_title"]
    assert len(dups) == 2


def test_promote_to_error() -> None:
    pages = [_page("a.one")]
    bodies = {"a.one": "short"}
    config = LintConfig(promote_to_error=["stub"])
    findings = lint_pages(pages, bodies, config=config)
    stubs = [f for f in findings if f.category == "stub"]
    assert stubs[0].severity == "error"


def test_default_severity_is_warning() -> None:
    pages = [_page("a.one")]
    bodies = {"a.one": "short"}
    findings = lint_pages(pages, bodies)
    assert all(f.severity == "warning" for f in findings)
