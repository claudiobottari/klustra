from __future__ import annotations

from klustra.linking import resolve_links


def test_all_links_resolve(valid_ids: set[str], body_with_links: str) -> None:
    result = resolve_links(body_with_links, valid_ids)
    assert len(result.resolved) == 3
    assert len(result.unresolved) == 0
    resolved_ids = {t.entity_id for t in result.resolved}
    assert resolved_ids == {"mat.copper", "prod.cable.xlpe-400kv", "proc.extrusion"}


def test_broken_links_detected(valid_ids: set[str], body_with_broken_links: str) -> None:
    result = resolve_links(body_with_broken_links, valid_ids)
    assert len(result.resolved) == 1
    assert result.resolved[0].entity_id == "mat.copper"
    assert len(result.unresolved) == 2
    unresolved_raws = {t.raw for t in result.unresolved}
    assert unresolved_raws == {"nonexistent.entity", "another.missing"}


def test_body_unchanged_on_broken_links(valid_ids: set[str], body_with_broken_links: str) -> None:
    result = resolve_links(body_with_broken_links, valid_ids)
    assert result.body == body_with_broken_links


def test_alias_resolution(valid_ids: set[str], aliases: dict[str, str]) -> None:
    body = "The [[P-Laser 320kV]] cable uses [[copper]] conductors."
    result = resolve_links(body, valid_ids, aliases=aliases)
    assert len(result.resolved) == 2
    assert len(result.unresolved) == 0
    assert result.resolved[0].raw == "P-Laser 320kV"
    assert result.resolved[0].entity_id == "prod.cable.p-laser-320kv"
    assert result.resolved[1].raw == "copper"
    assert result.resolved[1].entity_id == "mat.copper"


def test_self_link_detected(valid_ids: set[str]) -> None:
    body = "This page [[mat.copper]] references itself."
    result = resolve_links(body, valid_ids)
    assert len(result.resolved) == 1
    assert result.resolved[0].entity_id == "mat.copper"


def test_empty_link_is_unresolved(valid_ids: set[str]) -> None:
    body = "An empty link [[ ]] here."
    result = resolve_links(body, valid_ids)
    assert len(result.unresolved) == 1
    assert len(result.resolved) == 0


def test_no_links_in_body(valid_ids: set[str]) -> None:
    body = "Plain text with no wikilinks at all."
    result = resolve_links(body, valid_ids)
    assert len(result.resolved) == 0
    assert len(result.unresolved) == 0
    assert result.body == body


def test_duplicate_links_all_reported(valid_ids: set[str]) -> None:
    body = "First [[mat.copper]], then [[mat.copper]] again."
    result = resolve_links(body, valid_ids)
    assert len(result.resolved) == 2
    assert all(t.entity_id == "mat.copper" for t in result.resolved)
