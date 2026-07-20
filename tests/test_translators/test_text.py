from pathlib import Path

from klustra.translators.registry import build_default_registry
from klustra.translators.text import TextTranslator
from tests.test_translators.conftest import make_ctx, make_source

TRANSLATOR = TextTranslator()
CTX = make_ctx()


def test_single_unit(plain_txt: Path) -> None:
    src = make_source(plain_txt)
    result = TRANSLATOR.translate(src, CTX)
    assert len(result.units) == 1


def test_unit_kind_narrative(plain_txt: Path) -> None:
    src = make_source(plain_txt)
    result = TRANSLATOR.translate(src, CTX)
    assert result.units[0].kind == "narrative"


def test_locator_file(plain_txt: Path) -> None:
    src = make_source(plain_txt)
    result = TRANSLATOR.translate(src, CTX)
    assert result.units[0].locator == "file"


def test_unit_id_format(plain_txt: Path) -> None:
    src = make_source(plain_txt, source_id="src-001")
    result = TRANSLATOR.translate(src, CTX)
    assert result.units[0].unit_id == "src-001#0"


def test_unit_id_deterministic(plain_txt: Path) -> None:
    src = make_source(plain_txt, source_id="src-det")
    r1 = TRANSLATOR.translate(src, CTX)
    r2 = TRANSLATOR.translate(src, CTX)
    assert r1.units[0].unit_id == r2.units[0].unit_id


def test_content_preserved(plain_txt: Path) -> None:
    src = make_source(plain_txt)
    result = TRANSLATOR.translate(src, CTX)
    expected = plain_txt.read_text(encoding="utf-8")
    assert result.units[0].content_md == expected


def test_inherited_context_has_file_path(plain_txt: Path) -> None:
    src = make_source(plain_txt)
    result = TRANSLATOR.translate(src, CTX)
    assert result.units[0].inherited_context["file_path"] == str(plain_txt)


def test_source_metadata_has_file_path(plain_txt: Path) -> None:
    src = make_source(plain_txt)
    result = TRANSLATOR.translate(src, CTX)
    assert "file_path" in result.source_metadata


def test_empty_file_no_units(tmp_path: Path) -> None:
    f = tmp_path / "empty.txt"
    f.write_text("", encoding="utf-8")
    src = make_source(f)
    result = TRANSLATOR.translate(src, CTX)
    assert result.units == []


def test_whitespace_only_no_units(tmp_path: Path) -> None:
    f = tmp_path / "ws.txt"
    f.write_text("   \n\n  ", encoding="utf-8")
    src = make_source(f)
    result = TRANSLATOR.translate(src, CTX)
    assert result.units == []


def test_extensions() -> None:
    assert ".txt" in TRANSLATOR.extensions


# ---------------------------------------------------------------------------
# build_default_registry
# ---------------------------------------------------------------------------


def test_default_registry_has_txt() -> None:
    reg = build_default_registry()
    t = reg.get_for_path(Path("data.txt"))
    assert t.name == "text"


def test_default_registry_has_md() -> None:
    reg = build_default_registry()
    t = reg.get_for_path(Path("notes.md"))
    assert t.name == "markdown"


def test_default_registry_has_markdown_ext() -> None:
    reg = build_default_registry()
    t = reg.get_for_path(Path("notes.markdown"))
    assert t.name == "markdown"
