"""Shared fixtures for test_ingestion."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from klustra.core.file_state_store import FileStateStore
from klustra.core.source_ref import SourceRef
from klustra.ingestion.translator import TranslateContext, TranslationResult, Translator
from klustra.ingestion.translator_registry import TranslatorRegistry


class _TxtTranslator(Translator):
    name = "txt"
    version = "1.0"
    extensions = {".txt"}

    def translate(self, source: SourceRef, ctx: TranslateContext) -> TranslationResult:
        return TranslationResult(units=[], source_metadata={}, warnings=[])


class _MdTranslator(Translator):
    name = "md"
    version = "1.0"
    extensions = {".md"}
    schemes = {"mock"}

    def translate(self, source: SourceRef, ctx: TranslateContext) -> TranslationResult:
        return TranslationResult(units=[], source_metadata={}, warnings=[])


@pytest.fixture
def tmp_state(tmp_path: Path) -> FileStateStore:
    return FileStateStore(tmp_path)


@pytest.fixture
def txt_translator() -> _TxtTranslator:
    return _TxtTranslator()


@pytest.fixture
def md_translator() -> _MdTranslator:
    return _MdTranslator()


@pytest.fixture
def registry(txt_translator: _TxtTranslator, md_translator: _MdTranslator) -> TranslatorRegistry:
    reg = TranslatorRegistry()
    reg.register(txt_translator)
    reg.register(md_translator)
    return reg


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 7, 20, 12, 0, 0, tzinfo=UTC)
