import pytest
from pydantic import ValidationError

from klustra.core.changeset import ChangeSet, PageChanges, SourceChanges


def test_empty_changeset_defaults():
    cs = ChangeSet()
    assert cs.sources == SourceChanges()
    assert cs.pages == PageChanges()
    assert cs.sources.added == []


def test_populated_changeset():
    cs = ChangeSet(
        sources=SourceChanges(added=["sha256:a"], modified=["sha256:b"], removed=[]),
        pages=PageChanges(added=["x.y"], updated=[], removed=[], affected=["x.z"]),
    )
    assert cs.sources.added == ["sha256:a"]
    assert cs.pages.affected == ["x.z"]


def test_changeset_is_frozen():
    cs = ChangeSet()
    with pytest.raises(ValidationError):
        cs.sources = SourceChanges(added=["x"])
