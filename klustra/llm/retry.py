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
from klustra.llm.provider import LLMMessage, LLMRequest, LLMResponse

T = TypeVar("T")

DEFAULT_MAX_ATTEMPTS = 3

_SNIPPET_MAX_CHARS = 1000


def _is_retryable(exc: BaseException) -> bool:
    # LLMValidationError is deliberately NOT blind-retried here: at temperature 0
    # the same prompt reproduces the same bad output. It gets a corrective retry
    # with error feedback instead — see call_with_corrective_retry.
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


def _build_corrective_request(original: LLMRequest, exc: LLMValidationError) -> LLMRequest:
    """Append validation-error feedback for retry (same shape as the librarian citation retry)."""
    snippet = (exc.raw_content or "")[:_SNIPPET_MAX_CHARS]
    messages = [
        *original.messages,
        LLMMessage(role="assistant", content=snippet or "<empty response>"),
        LLMMessage(
            role="user",
            content=(
                f"REJECTED: your previous response was invalid: {exc}. "
                "Return ONLY valid JSON conforming to the schema — no prose, "
                "no markdown fences, no text before or after the JSON object, "
                "and make sure the JSON is complete and properly terminated."
            ),
        ),
    ]
    return LLMRequest(
        messages=messages,
        model=original.model,
        max_tokens=original.max_tokens,
        response_schema=original.response_schema,
        temperature=original.temperature,
    )


def call_with_corrective_retry(
    call_fn: Callable[[LLMRequest], LLMResponse],
    request: LLMRequest,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> LLMResponse:
    """Retry-with-feedback on LLMValidationError (CLAUDE.md rule 3).

    Each retry rebuilds from the ORIGINAL request plus the latest parse error and
    a snippet of the bad response — no unbounded message growth across attempts.
    Transient-failure backoff stays inside call_fn (llm_retry); no sleep needed
    here since a validation failure is not a rate/availability problem.
    """
    last_exc: LLMValidationError | None = None
    for attempt in range(1, max_attempts + 1):
        current = request if last_exc is None else _build_corrective_request(request, last_exc)
        try:
            return call_fn(current)
        except LLMValidationError as exc:
            last_exc = exc
            if attempt == max_attempts:
                raise
    raise AssertionError("unreachable")
