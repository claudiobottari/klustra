import pytest
from pydantic import ValidationError

from klustra.core.source_ref import SourceRef


def test_minimal_pre_translation_ref():
    ref = SourceRef(source_id="sha256:abc", source_path="C:/data/file.xlsx")
    assert ref.locator == ""
    assert ref.translator == ""


def test_full_provenance_ref():
    ref = SourceRef(
        source_id="sha256:abc",
        source_path="C:/data/file.xlsx",
        locator="sheet:Params!A1:F120",
        translator="excel@1.0",
    )
    assert ref.locator == "sheet:Params!A1:F120"
    assert ref.translator == "excel@1.0"


@pytest.mark.parametrize("field", ["source_id", "source_path"])
def test_blank_required_fields_rejected(field):
    kwargs = {"source_id": "sha256:abc", "source_path": "C:/data/file.xlsx"}
    kwargs[field] = "   "
    with pytest.raises(ValidationError):
        SourceRef(**kwargs)


def test_is_frozen():
    ref = SourceRef(source_id="sha256:abc", source_path="C:/data/file.xlsx")
    with pytest.raises(ValidationError):
        ref.source_id = "sha256:def"
