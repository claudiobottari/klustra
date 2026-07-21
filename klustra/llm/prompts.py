from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import BaseLoader, Environment, TemplateNotFound


class _OverrideLoader(BaseLoader):
    """Two-tier Jinja2 loader: override dir first, then package defaults."""

    def __init__(self, package_dir: Path, override_dir: Path | None) -> None:
        self._package_dir = package_dir
        self._override_dir = override_dir

    def get_source(self, environment: Environment, template: str) -> tuple[str, str, Any]:
        if self._override_dir is not None:
            override_path = self._override_dir / template
            if override_path.is_file():
                source = override_path.read_text(encoding="utf-8")
                return source, str(override_path), lambda: True

        pkg_path = self._package_dir / template
        if pkg_path.is_file():
            source = pkg_path.read_text(encoding="utf-8")
            return source, str(pkg_path), lambda: True

        raise TemplateNotFound(template)


class PromptRegistry:
    """Load and render Jinja2 prompt templates with .klustra override support (SPEC §10)."""

    def __init__(self, package_dir: Path | None = None, override_dir: Path | None = None) -> None:
        if package_dir is None:
            package_dir = Path(__file__).parent / "prompts"
        self._package_dir = package_dir
        self._override_dir = override_dir
        self._env = Environment(
            loader=_OverrideLoader(package_dir, override_dir),
            keep_trailing_newline=True,
        )

    def render(self, role: str, **context: Any) -> str:
        template = self._env.get_template(f"{role}.md")
        return template.render(**context)

    def list_roles(self) -> list[str]:
        roles: list[str] = []
        for p in self._package_dir.glob("*.md"):
            roles.append(p.stem)
        if self._override_dir is not None and self._override_dir.is_dir():
            for p in self._override_dir.glob("*.md"):
                if p.stem not in roles:
                    roles.append(p.stem)
        return sorted(roles)

    def is_overridden(self, role: str) -> bool:
        if self._override_dir is None:
            return False
        return (self._override_dir / f"{role}.md").is_file()
