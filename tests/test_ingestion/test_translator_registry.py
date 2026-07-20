from pathlib import Path

import pytest

from klustra.core.errors import TranslatorNotFoundError
from klustra.ingestion.translator_registry import TranslatorRegistry
from tests.test_ingestion.conftest import _TxtTranslator


def test_dispatch_by_extension(registry: TranslatorRegistry) -> None:
    t = registry.get_for_path(Path("report.txt"))
    assert t.name == "txt"


def test_dispatch_uppercase_extension(registry: TranslatorRegistry) -> None:
    t = registry.get_for_path(Path("REPORT.TXT"))
    assert t.name == "txt"


def test_dispatch_multiple_extensions() -> None:
    class MultiTranslator(_TxtTranslator):
        name = "multi"
        extensions = {".foo", ".bar"}

    reg = TranslatorRegistry()
    reg.register(MultiTranslator())
    assert reg.get_for_path(Path("a.foo")).name == "multi"
    assert reg.get_for_path(Path("a.bar")).name == "multi"


def test_dispatch_missing_extension_raises(registry: TranslatorRegistry) -> None:
    with pytest.raises(TranslatorNotFoundError):
        registry.get_for_path(Path("report.xlsx"))


def test_dispatch_by_scheme(registry: TranslatorRegistry) -> None:
    t = registry.get_for_scheme("mock")
    assert t.name == "md"


def test_dispatch_missing_scheme_raises(registry: TranslatorRegistry) -> None:
    from klustra.core.errors import TranslatorNotFoundError

    with pytest.raises(TranslatorNotFoundError):
        registry.get_for_scheme("sharepoint")


def test_register_last_write_wins() -> None:
    class V1(_TxtTranslator):
        name = "v1"

    class V2(_TxtTranslator):
        name = "v2"

    reg = TranslatorRegistry()
    reg.register(V1())
    reg.register(V2())
    assert reg.get_for_path(Path("f.txt")).name == "v2"


def test_extensions_and_schemes(registry: TranslatorRegistry) -> None:
    assert ".txt" in registry.extensions()
    assert ".md" in registry.extensions()
    assert "mock" in registry.schemes()
