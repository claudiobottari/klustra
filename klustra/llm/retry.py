from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from klustra.core.errors import LLMCallError, LLMValidationError

T = TypeVar("T")

DEFAULT_MAX_ATTEMPTS = 3


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, (LLMValidationError, KeyboardInterrupt)):
        return False
    if isinstance(exc, LLMCallError):
        return True
    return False


def _after_failure(state: RetryCallState) -> None:
    pass


def llm_retry(max_attempts: int = DEFAULT_MAX_ATTEMPTS) -> Callable[[Any], Any]:
    """Retry decorator for LLM calls: exponential backoff on transient failures."""
    return retry(
        retry=retry_if_exception(_is_retryable),
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=1, max=16),
        after=_after_failure,
        reraise=True,
    )
