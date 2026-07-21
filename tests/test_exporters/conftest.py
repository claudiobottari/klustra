from __future__ import annotations

from datetime import UTC, datetime

import pytest

from klustra.core.page import Page
from klustra.core.source_ref import SourceRef
from klustra.exporters.exporter import ExportContext, ExportPage


@pytest.fixture
def sample_pages() -> list[ExportPage]:
    """A small set of interlinked pages for export tests."""
    now = datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC)

    page_a = Page(
        type="concept",
        level=0,
        entity_id="mat.xlpe",
        title="XLPE Insulation",
        description="Cross-linked polyethylene insulation material.",
        domain="materials",
        tags=["insulation", "polymer"],
        aliases=["XLPE"],
        confidence=0.95,
        sources=[SourceRef(source_id="src001", source_path="/data/materials.xlsx")],
        created_at=now,
        updated_at=now,
    )

    page_b = Page(
        type="concept",
        level=0,
        entity_id="prod.cable.p-laser-320kv",
        title="P-Laser 320kV",
        description="A high-voltage cable product.",
        domain="products",
        tags=["cable", "hv"],
        aliases=["P-Laser"],
        confidence=0.9,
        sources=[
            SourceRef(source_id="src001", source_path="/data/materials.xlsx"),
            SourceRef(source_id="src002", source_path="/data/products.md"),
        ],
        created_at=now,
        updated_at=now,
    )

    page_c = Page(
        type="concept",
        level=0,
        entity_id="proc.extrusion",
        title="Extrusion Process",
        description="Manufacturing process for cable insulation.",
        domain="processes",
        tags=["manufacturing"],
        confidence=0.85,
        sources=[SourceRef(source_id="src003", source_path="/data/procs.md")],
        created_at=now,
        updated_at=now,
    )

    return [
        ExportPage(
            page=page_a,
            body_md=(
                "XLPE is a cross-linked polyethylene. ^[src001:sheet1:A2]\n\n"
                "Used in [[prod.cable.p-laser-320kv]] cables."
            ),
        ),
        ExportPage(
            page=page_b,
            body_md=(
                "The P-Laser 320kV uses [[mat.xlpe]] insulation. ^[src002:doc:1]\n\n"
                "Manufactured via [[proc.extrusion]]. ^[src001:sheet1:B5]"
            ),
        ),
        ExportPage(
            page=page_c,
            body_md=(
                "Extrusion applies heat and pressure to produce "
                "[[mat.xlpe]] insulation layers. ^[src003:doc:1]"
            ),
        ),
    ]


@pytest.fixture
def export_ctx() -> ExportContext:
    return ExportContext(run_id="test-run-001")
