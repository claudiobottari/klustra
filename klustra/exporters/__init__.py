from klustra.exporters.exporter import (
    ExportContext,
    Exporter,
    ExporterRegistry,
    ExportPage,
)
from klustra.exporters.obsidian import ObsidianExporter
from klustra.exporters.okf_bundle import OkfBundleExporter


def build_default_registry() -> ExporterRegistry:
    """Return an ExporterRegistry with all built-in exporters registered."""
    reg = ExporterRegistry()
    reg.register(ObsidianExporter())
    reg.register(OkfBundleExporter())
    return reg


__all__ = [
    "ExportContext",
    "ExportPage",
    "Exporter",
    "ExporterRegistry",
    "ObsidianExporter",
    "OkfBundleExporter",
    "build_default_registry",
]
