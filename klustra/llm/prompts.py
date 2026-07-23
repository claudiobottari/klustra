from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import BaseLoader, Environment, StrictUndefined, TemplateNotFound


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
            # A prompt silently missing a variable is a corrupted prompt, not a
            # cosmetic defect — Jinja2's default renders undefined as "".
            undefined=StrictUndefined,
        )

    def template_name(self, role: str, kind: str | None = None, version: str | None = None) -> str:
        """Resolve a template filename: `<role>[.<kind>][.<version>].md`.

        `kind` is system|user for roles that template both sides. `version`
        (e.g. "v2") lets a role gain a new revision without touching call
        sites; unversioned stays the active default. Both fall back to the
        plainer name when the more specific file does not exist, so the
        original `<role>.md` templates keep resolving unchanged.
        """
        segments = [s for s in (role, kind, version) if s]
        while len(segments) > 1:
            candidate = ".".join(segments) + ".md"
            if self._exists(candidate):
                return candidate
            segments.pop()  # drop the most specific segment and retry
        return f"{role}.md"

    def _exists(self, name: str) -> bool:
        if self._override_dir is not None and (self._override_dir / name).is_file():
            return True
        return (self._package_dir / name).is_file()

    def render(
        self,
        role: str,
        *,
        kind: str | None = None,
        version: str | None = None,
        **context: Any,
    ) -> str:
        template = self._env.get_template(self.template_name(role, kind, version))
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
