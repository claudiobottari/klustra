from __future__ import annotations

from klustra.linking import LinkEdge, build_link_graph, extract_links


def test_extract_links_basic() -> None:
    body = "Uses [[mat.copper]] and [[proc.extrusion]]."
    edges = extract_links("prod.cable.p-laser-320kv", body)
    assert len(edges) == 2
    assert edges[0] == LinkEdge(from_entity="prod.cable.p-laser-320kv", to_entity="mat.copper")
    assert edges[1] == LinkEdge(from_entity="prod.cable.p-laser-320kv", to_entity="proc.extrusion")


def test_extract_links_deduplicates() -> None:
    body = "[[mat.copper]] is great. [[mat.copper]] again."
    edges = extract_links("page.a", body)
    assert len(edges) == 1
    assert edges[0].to_entity == "mat.copper"


def test_extract_links_empty_body() -> None:
    edges = extract_links("page.a", "No links here.")
    assert edges == []


def test_extract_links_self_link() -> None:
    body = "This page [[page.a]] references itself."
    edges = extract_links("page.a", body)
    assert len(edges) == 1
    assert edges[0].from_entity == "page.a"
    assert edges[0].to_entity == "page.a"


def test_extract_links_ignores_empty_brackets() -> None:
    body = "An empty [[ ]] bracket."
    edges = extract_links("page.a", body)
    assert edges == []


def test_build_link_graph_multi_page(
    multi_page_fixture: list[tuple[str, str]],
) -> None:
    edges = build_link_graph(multi_page_fixture)
    assert len(edges) == 6

    from_counts: dict[str, int] = {}
    for e in edges:
        from_counts[e.from_entity] = from_counts.get(e.from_entity, 0) + 1

    assert from_counts["prod.cable.p-laser-320kv"] == 2
    assert from_counts["prod.cable.xlpe-400kv"] == 1
    assert from_counts["mat.copper"] == 2
    assert from_counts["proc.extrusion"] == 1


def test_build_link_graph_empty() -> None:
    edges = build_link_graph([])
    assert edges == []


def test_link_edge_frozen() -> None:
    edge = LinkEdge(from_entity="a", to_entity="b")
    try:
        edge.from_entity = "c"  # type: ignore[misc]
        raise AssertionError("Should not be mutable")
    except Exception:
        pass
