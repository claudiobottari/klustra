"""Shared fixtures for test_translators."""

from pathlib import Path

import pytest

from klustra.core.source_ref import SourceRef
from klustra.ingestion.translator import TranslateContext

FIXTURES = Path(__file__).parent.parent / "fixtures" / "translators"


def make_source(path: Path, source_id: str = "test0001") -> SourceRef:
    return SourceRef(source_id=source_id, source_path=str(path))


def make_ctx(run_id: str = "run-test") -> TranslateContext:
    return TranslateContext(run_id=run_id)


@pytest.fixture
def multi_section_md() -> Path:
    return FIXTURES / "multi_section.md"


@pytest.fixture
def no_heading_md() -> Path:
    return FIXTURES / "no_heading.md"


@pytest.fixture
def plain_txt() -> Path:
    return FIXTURES / "plain.txt"
