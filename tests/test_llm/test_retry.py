from __future__ import annotations

import pytest

from klustra.core.errors import LLMCallError, LLMValidationError
from klustra.llm.retry import DEFAULT_MAX_ATTEMPTS, llm_retry


def test_default_max_attempts_is_three() -> None:
    assert DEFAULT_MAX_ATTEMPTS == 3


def test_retry_succeeds_on_second_attempt() -> None:
    call_count = 0

    @llm_retry(max_attempts=3)
    def flaky() -> str:
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise LLMCallError("transient")
        return "ok"

    result = flaky()
    assert result == "ok"
    assert call_count == 2


def test_retry_exhausted_raises() -> None:
    @llm_retry(max_attempts=2)
    def always_fails() -> str:
        raise LLMCallError("permanent")

    with pytest.raises(LLMCallError, match="permanent"):
        always_fails()


def test_no_retry_on_validation_error() -> None:
    call_count = 0

    @llm_retry(max_attempts=3)
    def bad_schema() -> str:
        nonlocal call_count
        call_count += 1
        raise LLMValidationError("bad json")

    with pytest.raises(LLMValidationError):
        bad_schema()
    assert call_count == 1
