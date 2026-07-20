import pytest
from pydantic import ValidationError

from klustra.core.page import ClusterMeta, Page
from klustra.core.source_ref import SourceRef


def _base_kwargs(now, **overrides):
    kwargs = dict(
        type="concept",
        level=0,
        entity_id="prod.cable.p-laser-320kv",
        title="P-Laser 320kV",
        domain="engineering",
        confidence=0.92,
        created_at=now,
        updated_at=now,
    )
    kwargs.update(overrides)
    return kwargs


def test_minimal_level0_concept_page(now):
    page = Page(**_base_kwargs(now))
    assert page.level == 0
    assert page.sources == []
    assert page.schema_version == "1.0"


def test_level0_page_with_sources_and_memberships(now):
    page = Page(
        **_base_kwargs(
            now,
            sources=[
                SourceRef(
                    source_id="sha256:9f2a",
                    source_path="sharepoint://sites/RD/datasheets/PL320.pdf",
                    locator="page:4/table:2",
                    translator="pdf@1.0",
                )
            ],
            memberships=["cluster.engineering.l1.hvdc-secondary"],
        )
    )
    assert len(page.sources) == 1
    assert page.memberships == ["cluster.engineering.l1.hvdc-secondary"]


def test_cluster_page_with_children_and_cluster_meta(now):
    page = Page(
        **_base_kwargs(
            now,
            type="cluster",
            level=1,
            entity_id="cluster.engineering.l1.hvdc-cables",
            children=["prod.cable.p-laser-320kv", "prod.cable.p-laser-500kv"],
            cluster_meta=ClusterMeta(algo="hdbscan", run_id="run-1", cohesion=0.78),
        )
    )
    assert page.level == 1
    assert page.cluster_meta is not None
    assert page.cluster_meta.algo == "hdbscan"


def test_home_page(now):
    page = Page(
        **_base_kwargs(
            now,
            type="home",
            level=3,
            entity_id="cluster.engineering.home",
            cluster_meta=ClusterMeta(algo="gmm", run_id="run-2", cohesion=0.5),
        )
    )
    assert page.type == "home"


@pytest.mark.parametrize(
    "bad_id",
    ["Prod.Cable", "prod cable", "prod..cable", ".prod.cable", "prod.cable.", ""],
)
def test_invalid_entity_id_rejected(now, bad_id):
    with pytest.raises(ValidationError):
        Page(**_base_kwargs(now, entity_id=bad_id))


@pytest.mark.parametrize("confidence", [-0.1, 1.1])
def test_confidence_out_of_bounds_rejected(now, confidence):
    with pytest.raises(ValidationError):
        Page(**_base_kwargs(now, confidence=confidence))


def test_children_forbidden_at_level0(now):
    with pytest.raises(ValidationError, match="children"):
        Page(**_base_kwargs(now, children=["some.entity"]))


def test_sources_forbidden_above_level0(now):
    with pytest.raises(ValidationError, match="sources"):
        Page(
            **_base_kwargs(
                now,
                type="cluster",
                level=1,
                entity_id="cluster.engineering.l1.x",
                sources=[SourceRef(source_id="sha256:a", source_path="p")],
            )
        )


def test_memberships_forbidden_above_level0(now):
    with pytest.raises(ValidationError, match="memberships"):
        Page(
            **_base_kwargs(
                now,
                type="cluster",
                level=1,
                entity_id="cluster.engineering.l1.x",
                memberships=["some.entity"],
            )
        )


def test_cluster_meta_forbidden_for_non_cluster_home_type(now):
    with pytest.raises(ValidationError, match="cluster_meta"):
        Page(
            **_base_kwargs(
                now,
                cluster_meta=ClusterMeta(algo="hdbscan", run_id="run-1", cohesion=0.5),
            )
        )


def test_page_is_frozen(now):
    page = Page(**_base_kwargs(now))
    with pytest.raises(ValidationError):
        page.title = "changed"


def test_cluster_meta_cohesion_bounds():
    with pytest.raises(ValidationError):
        ClusterMeta(algo="hdbscan", run_id="run-1", cohesion=1.5)
