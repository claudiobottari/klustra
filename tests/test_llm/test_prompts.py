from __future__ import annotations

from pathlib import Path

import pytest

from klustra.llm.prompts import PromptRegistry


@pytest.fixture
def pkg_prompts(tmp_path: Path) -> Path:
    d = tmp_path / "prompts"
    d.mkdir()
    (d / "extraction.md").write_text("Extract: {{ topic }}", encoding="utf-8")
    (d / "librarian.md").write_text("Merge: {{ pages|length }} pages", encoding="utf-8")
    return d


@pytest.fixture
def override_dir(tmp_path: Path) -> Path:
    d = tmp_path / "override"
    d.mkdir()
    return d


def test_render_basic(pkg_prompts: Path) -> None:
    registry = PromptRegistry(package_dir=pkg_prompts)
    result = registry.render("extraction", topic="Python")
    assert result == "Extract: Python"


def test_render_with_filter(pkg_prompts: Path) -> None:
    registry = PromptRegistry(package_dir=pkg_prompts)
    result = registry.render("librarian", pages=["a", "b", "c"])
    assert result == "Merge: 3 pages"


def test_override_takes_precedence(pkg_prompts: Path, override_dir: Path) -> None:
    (override_dir / "extraction.md").write_text("Custom: {{ topic }}", encoding="utf-8")
    registry = PromptRegistry(package_dir=pkg_prompts, override_dir=override_dir)
    result = registry.render("extraction", topic="Go")
    assert result == "Custom: Go"


def test_list_roles(pkg_prompts: Path) -> None:
    registry = PromptRegistry(package_dir=pkg_prompts)
    roles = registry.list_roles()
    assert "extraction" in roles
    assert "librarian" in roles


def test_list_roles_includes_override_only(pkg_prompts: Path, override_dir: Path) -> None:
    (override_dir / "custom_role.md").write_text("Custom", encoding="utf-8")
    registry = PromptRegistry(package_dir=pkg_prompts, override_dir=override_dir)
    roles = registry.list_roles()
    assert "custom_role" in roles


def test_is_overridden(pkg_prompts: Path, override_dir: Path) -> None:
    (override_dir / "extraction.md").write_text("X", encoding="utf-8")
    registry = PromptRegistry(package_dir=pkg_prompts, override_dir=override_dir)
    assert registry.is_overridden("extraction") is True
    assert registry.is_overridden("librarian") is False


def test_missing_template_raises(pkg_prompts: Path) -> None:
    from jinja2 import TemplateNotFound

    registry = PromptRegistry(package_dir=pkg_prompts)
    with pytest.raises(TemplateNotFound):
        registry.render("nonexistent", topic="x")


# --- role prompt templates (SPEC §10): kind/version resolution + strictness ---

import re  # noqa: E402

from klustra.engine.librarian import LIBRARIAN_RULES  # noqa: E402

GOLDEN_DIR = Path(__file__).parent.parent / "fixtures" / "prompts"


def _librarian_system(registry: PromptRegistry | None = None, **overrides: object) -> str:
    ctx: dict = {"rules": LIBRARIAN_RULES, "domain_instructions": ""}
    ctx.update(overrides)
    return (registry or PromptRegistry()).render("librarian", kind="system", **ctx)


def test_librarian_system_renders_all_numbered_rules() -> None:
    out = _librarian_system()

    for i, rule in enumerate(LIBRARIAN_RULES, start=1):
        assert f"{i}. {rule}" in out
    numbers = [int(m) for m in re.findall(r"^(\d+)\. ", out, flags=re.MULTILINE)]
    assert numbers == list(range(1, len(LIBRARIAN_RULES) + 1)), "numbering must be contiguous"


def test_rendered_prompt_has_no_leftover_placeholders() -> None:
    out = _librarian_system()
    assert "{{" not in out and "}}" not in out
    assert "{%" not in out and "%}" not in out


def test_confidence_bound_survives_in_the_prompt_not_only_the_schema() -> None:
    """CLAUDE.md rule 10: third-party models treat the JSON schema as
    best-effort, so the bound must be stated in the system prompt too."""
    from klustra.engine.models import LIBRARIAN_SCHEMA

    out = _librarian_system()
    assert "[0.0, 1.0]" in out
    assert "1–10 scale" in out

    confidence = LIBRARIAN_SCHEMA["properties"]["confidence"]
    assert confidence["minimum"] == 0.0
    assert confidence["maximum"] == 1.0


def test_missing_required_variable_fails_loudly() -> None:
    """Jinja2's default silently renders undefined as "" — a prompt quietly
    missing its rules is a corrupted prompt, not a cosmetic defect."""
    from jinja2 import UndefinedError

    with pytest.raises(UndefinedError):
        PromptRegistry().render("librarian", kind="system", domain_instructions="")

    with pytest.raises(UndefinedError):
        PromptRegistry().render("extraction", kind="user", index_str="x")


def test_domain_instructions_render_into_the_template_when_present() -> None:
    out = _librarian_system(domain_instructions="Prefer Italian terminology.")
    assert "## Domain instructions" in out
    assert "Prefer Italian terminology." in out


def test_domain_instructions_absent_leaves_prompt_byte_identical() -> None:
    """The insertion point must be inert when no domain instructions exist."""
    assert "Domain instructions" not in _librarian_system()
    assert "Domain instructions" not in PromptRegistry().render(
        "extraction", kind="system", domain_instructions=""
    )


@pytest.mark.parametrize(
    ("role", "golden"),
    [("librarian", "librarian.system.golden.md"), ("extraction", "extraction.system.golden.md")],
)
def test_system_prompt_matches_golden_snapshot(role: str, golden: str) -> None:
    """Guards against unintended prompt wording drift — update the fixture
    deliberately when a prompt change is the point."""
    ctx: dict = {"domain_instructions": ""}
    if role == "librarian":
        ctx["rules"] = LIBRARIAN_RULES
    rendered = PromptRegistry().render(role, kind="system", **ctx)
    expected = (GOLDEN_DIR / golden).read_text(encoding="utf-8")
    assert rendered == expected


def test_template_name_resolves_kind_and_version_with_fallback(tmp_path: Path) -> None:
    """Call sites never bake in a version, so adding v2 later is additive."""
    pkg = tmp_path / "prompts"
    pkg.mkdir()
    (pkg / "librarian.md").write_text("plain", encoding="utf-8")
    registry = PromptRegistry(package_dir=pkg)

    # Only the plain file exists — everything falls back to it.
    assert registry.template_name("librarian") == "librarian.md"
    assert registry.template_name("librarian", "system") == "librarian.md"
    assert registry.template_name("librarian", "system", "v2") == "librarian.md"

    (pkg / "librarian.system.md").write_text("sys", encoding="utf-8")
    assert registry.template_name("librarian", "system") == "librarian.system.md"
    assert registry.template_name("librarian", "system", "v2") == "librarian.system.md"

    (pkg / "librarian.system.v2.md").write_text("sys v2", encoding="utf-8")
    assert registry.template_name("librarian", "system", "v2") == "librarian.system.v2.md"
    assert registry.template_name("librarian", "system") == "librarian.system.md", (
        "unversioned stays the active default"
    )


def test_existing_single_file_roles_still_resolve_without_kind() -> None:
    """hierarchy/home/judge predate the <role>.<kind> split and must be untouched."""
    registry = PromptRegistry()
    for role in ("hierarchy", "home", "judge"):
        assert registry.template_name(role) == f"{role}.md"


def test_role_templates_can_be_overridden_per_project(tmp_path: Path) -> None:
    override = tmp_path / "prompts"
    override.mkdir()
    (override / "librarian.system.md").write_text("CUSTOM {{ rules | length }}", encoding="utf-8")

    registry = PromptRegistry(override_dir=override)
    assert _librarian_system(registry) == f"CUSTOM {len(LIBRARIAN_RULES)}"
    assert registry.is_overridden("librarian.system")
