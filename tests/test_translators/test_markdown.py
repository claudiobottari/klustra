from pathlib import Path

from klustra.translators.markdown import MarkdownTranslator, _split_md_sections
from tests.test_translators.conftest import make_ctx, make_source

TRANSLATOR = MarkdownTranslator()
CTX = make_ctx()


# ---------------------------------------------------------------------------
# _split_md_sections unit tests
# ---------------------------------------------------------------------------


def test_split_preamble_and_sections() -> None:
    text = "Preamble.\n\n# Intro\n\nIntro text.\n\n# Conclusion\n\nBye.\n"
    sections = _split_md_sections(text)
    assert len(sections) == 3
    headings = [h for h, _ in sections]
    assert headings == ["", "Intro", "Conclusion"]


def test_split_no_heading() -> None:
    text = "Just text.\n\nNo headings.\n"
    sections = _split_md_sections(text)
    assert len(sections) == 1
    assert sections[0][0] == ""


def test_split_starts_with_heading() -> None:
    text = "# First\n\nContent.\n# Second\n\nMore.\n"
    sections = _split_md_sections(text)
    assert len(sections) == 2
    assert sections[0][0] == "First"
    assert sections[1][0] == "Second"


def test_split_content_includes_heading_line() -> None:
    text = "# Hello\n\nBody text.\n"
    sections = _split_md_sections(text)
    assert "# Hello" in sections[0][1]
    assert "Body text." in sections[0][1]


def test_split_second_level_heading_not_split() -> None:
    text = "# Top\n\n## Sub\n\nSub content.\n"
    sections = _split_md_sections(text)
    assert len(sections) == 1
    assert "## Sub" in sections[0][1]


def test_split_empty_text() -> None:
    assert _split_md_sections("") == []


def test_split_whitespace_only() -> None:
    assert _split_md_sections("   \n\n  ") == []


# ---------------------------------------------------------------------------
# MarkdownTranslator.translate — multi_section.md
# ---------------------------------------------------------------------------


def test_multi_section_unit_count(multi_section_md: Path) -> None:
    src = make_source(multi_section_md)
    result = TRANSLATOR.translate(src, CTX)
    # preamble + Introduction + Background + Conclusion = 4
    assert len(result.units) == 4


def test_multi_section_locators(multi_section_md: Path) -> None:
    src = make_source(multi_section_md)
    result = TRANSLATOR.translate(src, CTX)
    locators = [u.locator for u in result.units]
    assert locators[0] == "preamble"
    assert locators[1] == "section:Introduction"
    assert locators[2] == "section:Background"
    assert locators[3] == "section:Conclusion"


def test_multi_section_unit_ids_deterministic(multi_section_md: Path) -> None:
    src = make_source(multi_section_md, source_id="src-abc")
    r1 = TRANSLATOR.translate(src, CTX)
    r2 = TRANSLATOR.translate(src, CTX)
    assert [u.unit_id for u in r1.units] == [u.unit_id for u in r2.units]
    assert r1.units[0].unit_id == "src-abc#0"
    assert r1.units[3].unit_id == "src-abc#3"


def test_multi_section_all_narrative(multi_section_md: Path) -> None:
    src = make_source(multi_section_md)
    for unit in TRANSLATOR.translate(src, CTX).units:
        assert unit.kind == "narrative"


def test_multi_section_inherited_context_heading(multi_section_md: Path) -> None:
    src = make_source(multi_section_md)
    units = TRANSLATOR.translate(src, CTX).units
    assert units[0].inherited_context["heading"] is None  # preamble
    assert units[1].inherited_context["heading"] == "Introduction"
    assert units[2].inherited_context["heading"] == "Background"


def test_multi_section_content_includes_heading(multi_section_md: Path) -> None:
    src = make_source(multi_section_md)
    units = TRANSLATOR.translate(src, CTX).units
    assert "# Introduction" in units[1].content_md
    assert "# Background" in units[2].content_md


def test_multi_section_subsection_not_split(multi_section_md: Path) -> None:
    src = make_source(multi_section_md)
    units = TRANSLATOR.translate(src, CTX).units
    background_unit = next(u for u in units if u.locator == "section:Background")
    assert "## Subsection" in background_unit.content_md


def test_multi_section_source_metadata(multi_section_md: Path) -> None:
    src = make_source(multi_section_md)
    result = TRANSLATOR.translate(src, CTX)
    assert result.source_metadata["sections"] == 4
    assert "file_path" in result.source_metadata


# ---------------------------------------------------------------------------
# MarkdownTranslator.translate — no_heading.md
# ---------------------------------------------------------------------------


def test_no_heading_single_unit(no_heading_md: Path) -> None:
    src = make_source(no_heading_md)
    result = TRANSLATOR.translate(src, CTX)
    assert len(result.units) == 1


def test_no_heading_locator_file(no_heading_md: Path) -> None:
    src = make_source(no_heading_md)
    result = TRANSLATOR.translate(src, CTX)
    assert result.units[0].locator == "file"


def test_no_heading_unit_id(no_heading_md: Path) -> None:
    src = make_source(no_heading_md, source_id="src-xyz")
    result = TRANSLATOR.translate(src, CTX)
    assert result.units[0].unit_id == "src-xyz#0"


# ---------------------------------------------------------------------------
# MarkdownTranslator.translate — edge cases with tmp files
# ---------------------------------------------------------------------------


def test_empty_file_no_units(tmp_path: Path) -> None:
    f = tmp_path / "empty.md"
    f.write_text("", encoding="utf-8")
    src = make_source(f)
    result = TRANSLATOR.translate(src, CTX)
    assert result.units == []


def test_whitespace_only_no_units(tmp_path: Path) -> None:
    f = tmp_path / "ws.md"
    f.write_text("\n\n  \n", encoding="utf-8")
    src = make_source(f)
    result = TRANSLATOR.translate(src, CTX)
    assert result.units == []


def test_heading_only_produces_unit(tmp_path: Path) -> None:
    f = tmp_path / "heading_only.md"
    f.write_text("# Just a Heading\n", encoding="utf-8")
    src = make_source(f)
    result = TRANSLATOR.translate(src, CTX)
    assert len(result.units) == 1
    assert result.units[0].locator == "section:Just a Heading"


# ---------------------------------------------------------------------------
# Extensions
# ---------------------------------------------------------------------------


def test_extensions() -> None:
    assert ".md" in TRANSLATOR.extensions
    assert ".markdown" in TRANSLATOR.extensions
