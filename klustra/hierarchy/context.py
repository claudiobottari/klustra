"""Context, navigate, and search API (SPEC §7)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from klustra.core.page import PageType
from klustra.hierarchy.incremental import cosine_distance


class PageSummary(BaseModel):
    """Lightweight page view for hierarchy traversal."""

    model_config = ConfigDict(frozen=True)

    entity_id: str
    title: str
    description: str = ""
    level: int
    type: PageType
    children: list[str] = Field(default_factory=list)


class AncestorInfo(BaseModel):
    """Title + description of an ancestor page (parsimonious context)."""

    model_config = ConfigDict(frozen=True)

    entity_id: str
    title: str
    description: str = ""
    level: int


class ConceptContext(BaseModel):
    """Result of context() — page + ancestor chain + optional siblings."""

    model_config = ConfigDict(frozen=True)

    page: PageSummary
    ancestors: list[AncestorInfo] = Field(default_factory=list)
    siblings: list[PageSummary] = Field(default_factory=list)


class NavigateResult(BaseModel):
    """Result of navigate() — current page + children."""

    model_config = ConfigDict(frozen=True)

    current: PageSummary
    children: list[PageSummary] = Field(default_factory=list)


class SearchHit(BaseModel):
    """One result from search()."""

    model_config = ConfigDict(frozen=True)

    entity_id: str
    title: str
    description: str = ""
    level: int
    score: float = Field(ge=0.0, le=1.0)


def build_parent_map(pages: dict[str, PageSummary]) -> dict[str, str]:
    """Invert children lists to build child_id → parent_id map."""
    parent_map: dict[str, str] = {}
    for page in pages.values():
        for child_id in page.children:
            parent_map[child_id] = page.entity_id
    return parent_map


def context(
    entity_id: str,
    pages: dict[str, PageSummary],
    *,
    depth: int = 1,
    include: tuple[str, ...] = ("ancestors",),
) -> ConceptContext:
    """Parsimonious context: page + ancestor chain (zero LLM). SPEC §7.2."""
    page = pages.get(entity_id)
    if page is None:
        raise KeyError(f"Entity '{entity_id}' not found")

    ancestors: list[AncestorInfo] = []
    siblings: list[PageSummary] = []

    if "ancestors" in include:
        parent_map = build_parent_map(pages)
        current_id = entity_id
        steps = 0
        while current_id in parent_map and (depth == -1 or steps < depth):
            parent_id = parent_map[current_id]
            parent_page = pages.get(parent_id)
            if parent_page is None:
                break
            ancestors.append(
                AncestorInfo(
                    entity_id=parent_page.entity_id,
                    title=parent_page.title,
                    description=parent_page.description,
                    level=parent_page.level,
                )
            )
            current_id = parent_id
            steps += 1

    if "siblings" in include:
        parent_map_sib = build_parent_map(pages)
        sib_parent_id = parent_map_sib.get(entity_id)
        if sib_parent_id is not None:
            parent_page = pages.get(sib_parent_id)
            if parent_page is not None:
                for child_id in parent_page.children:
                    if child_id != entity_id:
                        child_page = pages.get(child_id)
                        if child_page is not None:
                            siblings.append(child_page)

    return ConceptContext(page=page, ancestors=ancestors, siblings=siblings)


def navigate(
    pages: dict[str, PageSummary],
    from_entity_id: str | None = None,
) -> NavigateResult:
    """Guided descent: home → children. SPEC §7.1."""
    if from_entity_id is None:
        home = _find_home(pages)
        if home is None:
            raise KeyError("No home page found")
        current = home
    else:
        found = pages.get(from_entity_id)
        if found is None:
            raise KeyError(f"Entity '{from_entity_id}' not found")
        current = found

    children: list[PageSummary] = []
    for child_id in current.children:
        child_page = pages.get(child_id)
        if child_page is not None:
            children.append(child_page)

    return NavigateResult(current=current, children=children)


def search(
    query_embedding: list[float],
    page_embeddings: dict[str, list[float]],
    pages: dict[str, PageSummary],
    *,
    level: int | None = None,
    mode: Literal["collapsed", "tree"] = "collapsed",
    top_k: int = 10,
) -> list[SearchHit]:
    """Ranked search across hierarchy levels. SPEC §7.3."""
    if mode == "collapsed":
        return _search_collapsed(query_embedding, page_embeddings, pages, level, top_k)
    else:
        return _search_tree(query_embedding, page_embeddings, pages, top_k)


def _search_collapsed(
    query_embedding: list[float],
    page_embeddings: dict[str, list[float]],
    pages: dict[str, PageSummary],
    level: int | None,
    top_k: int,
) -> list[SearchHit]:
    """Collapsed-tree: all levels in one vector space, ranked by similarity."""
    scored: list[tuple[float, str]] = []

    for eid, emb in page_embeddings.items():
        page = pages.get(eid)
        if page is None:
            continue
        if level is not None and page.level != level:
            continue
        dist = cosine_distance(query_embedding, emb)
        similarity = 1.0 - dist
        scored.append((similarity, eid))

    scored.sort(key=lambda x: x[0], reverse=True)

    hits: list[SearchHit] = []
    for score, eid in scored[:top_k]:
        page = pages[eid]
        hits.append(
            SearchHit(
                entity_id=eid,
                title=page.title,
                description=page.description,
                level=page.level,
                score=max(0.0, min(1.0, score)),
            )
        )
    return hits


def _search_tree(
    query_embedding: list[float],
    page_embeddings: dict[str, list[float]],
    pages: dict[str, PageSummary],
    top_k: int,
) -> list[SearchHit]:
    """Tree-mode: top-down traversal with pruning per level."""
    home = _find_home(pages)
    if home is None:
        return []

    results: list[SearchHit] = []
    frontier = [home.entity_id]

    while frontier and len(results) < top_k:
        scored: list[tuple[float, str]] = []
        for eid in frontier:
            emb = page_embeddings.get(eid)
            if emb is None:
                continue
            dist = cosine_distance(query_embedding, emb)
            similarity = 1.0 - dist
            scored.append((similarity, eid))

        scored.sort(key=lambda x: x[0], reverse=True)

        next_frontier: list[str] = []
        for score, eid in scored[:top_k]:
            page = pages.get(eid)
            if page is None:
                continue
            results.append(
                SearchHit(
                    entity_id=eid,
                    title=page.title,
                    description=page.description,
                    level=page.level,
                    score=max(0.0, min(1.0, score)),
                )
            )
            next_frontier.extend(page.children)

        frontier = next_frontier

    return results[:top_k]


def _find_home(pages: dict[str, PageSummary]) -> PageSummary | None:
    """Find the home page in the pages dict."""
    for page in pages.values():
        if page.type == "home":
            return page
    return None
