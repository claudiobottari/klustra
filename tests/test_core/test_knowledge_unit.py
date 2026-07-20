import pytest
from pydantic import ValidationError

from klustra.core.knowledge_unit import KnowledgeUnit


def test_table_unit_with_records():
    unit = KnowledgeUnit(
        unit_id="sha256:abc#1",
        kind="table",
        content_md="| a | b |\n|---|---|\n| 1 | 2 |",
        records=[{"a": 1, "b": 2}],
        locator="sheet:Params!A1:F120",
        inherited_context={"sheet_name": "Params"},
    )
    assert unit.kind == "table"
    assert unit.records == [{"a": 1, "b": 2}]


def test_narrative_unit_without_records():
    unit = KnowledgeUnit(
        unit_id="sha256:abc#2",
        kind="narrative",
        content_md="Some free text.",
        locator="page:4",
    )
    assert unit.records is None
    assert unit.inherited_context == {}


def test_invalid_kind_rejected():
    with pytest.raises(ValidationError):
        KnowledgeUnit(
            unit_id="sha256:abc#1",
            kind="paragraph",
            content_md="x",
            locator="page:1",
        )


@pytest.mark.parametrize("field", ["unit_id", "locator"])
def test_blank_required_fields_rejected(field):
    kwargs = {
        "unit_id": "sha256:abc#1",
        "kind": "narrative",
        "content_md": "x",
        "locator": "page:1",
    }
    kwargs[field] = "  "
    with pytest.raises(ValidationError):
        KnowledgeUnit(**kwargs)
