from __future__ import annotations

from datetime import UTC, datetime

import pytest

from klustra.core.knowledge_unit import KnowledgeUnit
from klustra.core.page import Page
from klustra.core.state_store import PageRecord
from klustra.llm import MockProvider


@pytest.fixture
def mock_provider() -> MockProvider:
    return MockProvider()


@pytest.fixture
def sample_units() -> list[KnowledgeUnit]:
    return [
        KnowledgeUnit(
            unit_id="src001#1",
            kind="narrative",
            content_md="P-Laser 320kV is a high-voltage cable using XLPE insulation.",
            locator="sheet1:A1",
        ),
        KnowledgeUnit(
            unit_id="src001#2",
            kind="table",
            content_md=(
                "| Cable | Voltage | Insulation |\n|---|---|---|\n| P-Laser | 320kV | XLPE |"
            ),
            locator="sheet1:A5",
        ),
    ]


@pytest.fixture
def sample_page_records() -> list[PageRecord]:
    return [
        PageRecord(
            entity_id="prod.cable.p-laser-320kv",
            source_ids=["src001", "src002"],
            level=0,
            content_hash="aaa",
        ),
        PageRecord(
            entity_id="mat.xlpe",
            source_ids=["src002", "src003"],
            level=0,
            content_hash="bbb",
        ),
        PageRecord(
            entity_id="proc.extrusion",
            source_ids=["src003"],
            level=0,
            content_hash="ccc",
        ),
    ]


def _make_page(
    entity_id: str,
    title: str = "Test Page",
    level: int = 0,
    page_type: str = "concept",
    children: list[str] | None = None,
) -> Page:
    now = datetime.now(UTC)
    return Page(
        type=page_type,  # type: ignore[arg-type]
        level=level,
        entity_id=entity_id,
        title=title,
        domain="test",
        confidence=0.9,
        created_at=now,
        updated_at=now,
        children=children or [],
    )


@pytest.fixture
def sample_pages() -> list[Page]:
    return [
        _make_page(
            "cluster.cables",
            title="Cables",
            level=1,
            page_type="cluster",
            children=["prod.cable.p-laser-320kv", "prod.cable.xlpe-400kv"],
        ),
        _make_page("prod.cable.p-laser-320kv", title="P-Laser 320kV"),
        _make_page("prod.cable.xlpe-400kv", title="XLPE 400kV"),
        _make_page("mat.copper", title="Copper"),
    ]
