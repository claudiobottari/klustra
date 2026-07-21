"""Cluster stability — Jaccard matching between runs (SPEC §6.3)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class OldCluster(BaseModel):
    """A cluster from the previous hierarchy run."""

    model_config = ConfigDict(frozen=True)

    entity_id: str
    children: list[str]


class NewCluster(BaseModel):
    """A cluster from the current hierarchy run (tentative entity_id)."""

    model_config = ConfigDict(frozen=True)

    entity_id: str
    children: list[str]


class ClusterMatch(BaseModel):
    """Result of matching one new cluster against old clusters."""

    model_config = ConfigDict(frozen=True)

    new_index: int
    old_entity_id: str
    new_entity_id: str = Field(description="= old_entity_id if inherited")
    jaccard: float = Field(ge=0.0, le=1.0)
    inherited: bool


class StabilityResult(BaseModel):
    """Output of match_clusters()."""

    model_config = ConfigDict(frozen=True)

    matches: list[ClusterMatch] = Field(default_factory=list)
    superseded: dict[str, str] = Field(
        default_factory=dict, description="old_entity_id → new_entity_id that replaced it"
    )
    new_ids: list[str] = Field(
        default_factory=list, description="Truly new cluster entity_ids (no old match)"
    )


def jaccard_similarity(a: set[str], b: set[str]) -> float:
    """Jaccard index: |A ∩ B| / |A ∪ B|."""
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def match_clusters(
    old_clusters: list[OldCluster],
    new_clusters: list[NewCluster],
    threshold: float = 0.6,
) -> StabilityResult:
    """Match new clusters to old via Jaccard similarity (SPEC §6.3).

    Greedy best-match: highest Jaccard first, each old matches at most one new.
    If Jaccard >= threshold: new inherits old entity_id.
    Else: new keeps tentative id; unmatched old is superseded.
    """
    scores: list[tuple[float, int, int]] = []
    for ni, new_c in enumerate(new_clusters):
        new_set = set(new_c.children)
        for oi, old_c in enumerate(old_clusters):
            old_set = set(old_c.children)
            j = jaccard_similarity(new_set, old_set)
            if j > 0:
                scores.append((j, ni, oi))

    scores.sort(key=lambda x: x[0], reverse=True)

    matched_old: set[int] = set()
    matched_new: set[int] = set()
    matches: list[ClusterMatch] = []

    for j, ni, oi in scores:
        if ni in matched_new or oi in matched_old:
            continue
        inherited = j >= threshold
        entity_id = old_clusters[oi].entity_id if inherited else new_clusters[ni].entity_id
        matches.append(
            ClusterMatch(
                new_index=ni,
                old_entity_id=old_clusters[oi].entity_id,
                new_entity_id=entity_id,
                jaccard=j,
                inherited=inherited,
            )
        )
        matched_old.add(oi)
        matched_new.add(ni)

    superseded: dict[str, str] = {}
    for oi, old_c in enumerate(old_clusters):
        if oi not in matched_old:
            best_new = _best_new_for_old(old_c, new_clusters, matched_new)
            if best_new is not None:
                superseded[old_c.entity_id] = new_clusters[best_new].entity_id
            else:
                superseded[old_c.entity_id] = ""

    new_ids: list[str] = []
    for ni, new_c in enumerate(new_clusters):
        if ni not in matched_new:
            new_ids.append(new_c.entity_id)

    return StabilityResult(
        matches=matches,
        superseded=superseded,
        new_ids=new_ids,
    )


def _best_new_for_old(
    old: OldCluster,
    new_clusters: list[NewCluster],
    excluded: set[int],
) -> int | None:
    """Find the best-matching new cluster for a superseded old cluster."""
    old_set = set(old.children)
    best_j = 0.0
    best_idx: int | None = None
    for ni, new_c in enumerate(new_clusters):
        if ni in excluded:
            continue
        j = jaccard_similarity(old_set, set(new_c.children))
        if j > best_j:
            best_j = j
            best_idx = ni
    return best_idx


def resolve_superseded(entity_id: str, superseded_map: dict[str, str]) -> str:
    """Follow superseded_by chain to find the final active entity_id."""
    seen: set[str] = set()
    current = entity_id
    while current in superseded_map and superseded_map[current]:
        if current in seen:
            break
        seen.add(current)
        current = superseded_map[current]
    return current
