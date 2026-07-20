import pytest

from klustra.core.errors import (
    ConfigError,
    ConformanceError,
    KlustraError,
    PageNotFoundError,
    SourceNotFoundError,
    StateStoreError,
)


@pytest.mark.parametrize(
    "exc_cls",
    [ConfigError, ConformanceError, StateStoreError, SourceNotFoundError, PageNotFoundError],
)
def test_all_domain_errors_are_klustra_errors(exc_cls):
    assert issubclass(exc_cls, KlustraError)


def test_not_found_errors_are_state_store_errors():
    assert issubclass(SourceNotFoundError, StateStoreError)
    assert issubclass(PageNotFoundError, StateStoreError)


def test_errors_carry_message():
    with pytest.raises(KlustraError, match="boom"):
        raise ConfigError("boom")
