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
