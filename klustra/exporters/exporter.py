from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from klustra.core.errors import ExporterNotFoundError
from klustra.core.page import Page


class ExportPage(BaseModel):
    """A page + its body markdown, ready for export."""

    model_config = ConfigDict(frozen=True)

    page: Page
    body_md: str


class ExportContext(BaseModel):
    """Execution context passed to every Exporter.export() call."""

    model_config = ConfigDict(frozen=True)

    run_id: str


class Exporter(ABC):
    """Strategy contract for exporters (SPEC §11)."""

    name: str

    @abstractmethod
    def export(self, pages: list[ExportPage], output_dir: Path, ctx: ExportContext) -> None: ...


class ExporterRegistry:
    """Maps exporter names to Exporter instances."""

    def __init__(self) -> None:
        self._registry: dict[str, Exporter] = {}

    def register(self, exporter: Exporter) -> None:
        self._registry[exporter.name] = exporter

    def get(self, name: str) -> Exporter:
        if name not in self._registry:
            raise ExporterNotFoundError(f"No exporter registered for name {name!r}")
        return self._registry[name]

    def names(self) -> frozenset[str]:
        return frozenset(self._registry)
