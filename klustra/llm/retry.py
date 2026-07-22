from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, TypeVar

from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from klustra.core.errors import LLMCallError, LLMRateLimitError, LLMValidationError
from klustra.llm.provider import LLMMessage, LLMRequest, LLMResponse

T = TypeVar("T")

logger = logging.getLogger(__name__)

DEFAULT_MAX_ATTEMPTS = 3

_SNIPPET_MAX_CHARS = 1000

# Transient-failure backoff. Rate limits/overload ("provider temporarily
# overloaded") resolve in seconds-to-minutes, not milliseconds — deliberately
# slower and longer than the default backoff for other transient LLMCallErrors.
_DEFAULT_WAIT = wait_exponential(multiplier=1, min=1, max=16)
_RATE_LIMIT_WAIT = wait_exponential(multiplier=2, min=2, max=60)


def _is_retryable(exc: BaseException) -> bool:
    # LLMValidationError is deliberately NOT blind-retried here: at temperature 0
    # the same prompt reproduces the same bad output. It gets a corrective retry
    # with error feedback instead — see call_with_corrective_retry.
    if isinstance(exc, (LLMValidationError, KeyboardInterrupt)):
        return False
    if isinstance(exc, LLMCallError):
        return True
    return False


def _find_request(retry_state: RetryCallState) -> LLMRequest | None:
    """Locate the LLMRequest among the retried call's args/kwargs, if any.

    Lets stop/wait/logging stay dynamic per-request (retry_attempts, label)
    while `_call_with_retry(self, request)` stays a plain @llm_retry()-decorated
    method — no per-call decorator construction needed.
    """
    for a in retry_state.args or ():
        if isinstance(a, LLMRequest):
            return a
    for v in (retry_state.kwargs or {}).values():
        if isinstance(v, LLMRequest):
            return v
    return None


def _max_attempts_for(retry_state: RetryCallState, fallback: int) -> int:
    request = _find_request(retry_state)
    if request is not None and request.retry_attempts is not None:
        return request.retry_attempts
    return fallback


def _dynamic_stop(retry_state: RetryCallState) -> bool:
    return retry_state.attempt_number >= _max_attempts_for(retry_state, DEFAULT_MAX_ATTEMPTS)


def _wait_strategy(retry_state: RetryCallState) -> float:
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    if isinstance(exc, LLMRateLimitError):
        return _RATE_LIMIT_WAIT(retry_state)
    return _DEFAULT_WAIT(retry_state)


def _before_sleep(retry_state: RetryCallState) -> None:
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    request = _find_request(retry_state)
    max_attempts = _max_attempts_for(retry_state, DEFAULT_MAX_ATTEMPTS)
    label = (request.label if request and request.label else None) or (
        request.model if request else "?"
    )
    kind = "rate-limited/overloaded" if isinstance(exc, LLMRateLimitError) else "transient error"
    logger.warning(
        "[llm] retrying %s call (attempt %d/%d) after %s: %s",
        label,
        retry_state.attempt_number + 1,
        max_attempts,
        kind,
        exc,
    )


def llm_retry(max_attempts: int | None = None) -> Callable[[Any], Any]:
    """Retry decorator for LLM calls: exponential backoff on transient failures.

    max_attempts=None (default): read per-call from LLMRequest.retry_attempts
    (LLMRoleConfig.retry_attempts), falling back to DEFAULT_MAX_ATTEMPTS when the
    wrapped call carries no LLMRequest or leaves it unset. Pass an explicit int
    to force a fixed attempt count regardless of the request (used by tests).
    """
    stop = stop_after_attempt(max_attempts) if max_attempts is not None else _dynamic_stop
    return retry(
        retry=retry_if_exception(_is_retryable),
        stop=stop,
        wait=_wait_strategy,
        before_sleep=_before_sleep,
        reraise=True,
    )


def is_rate_limit_error(status_code: int, body: object) -> bool:
    """429, or OpenRouter's provider_error_code == 'engine_overloaded' in the body."""
    if status_code == 429:
        return True
    return _contains_engine_overloaded(body)


def _contains_engine_overloaded(body: object) -> bool:
    if isinstance(body, dict):
        for key, value in body.items():
            if key == "provider_error_code" and value == "engine_overloaded":
                return True
            if _contains_engine_overloaded(value):
                return True
        return False
    if isinstance(body, list):
        return any(_contains_engine_overloaded(item) for item in body)
    return False


def find_body_model_ref(body: object) -> str | None:
    """Scan an error body for a 'model' field — diagnostic for whether the model name
    a provider echoes back in a 429/error body matches the model we requested."""
    if isinstance(body, dict):
        value = body.get("model")
        if isinstance(value, str):
            return value
        for v in body.values():
            found = find_body_model_ref(v)
            if found is not None:
                return found
        return None
    if isinstance(body, list):
        for item in body:
            found = find_body_model_ref(item)
            if found is not None:
                return found
    return None


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
        retry_attempts=original.retry_attempts,
        label=original.label,
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
    here since a validation failure is not a rate/availability problem. This loop
    is deliberately separate from the transient-failure backoff above: JSON
    validation failures are not rate limits and must not share their attempt
    budget or wait strategy.
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
            label = request.label or request.model
            logger.warning(
                "[llm] retrying %s call (attempt %d/%d): invalid response, "
                "requesting correction: %s",
                label,
                attempt + 1,
                max_attempts,
                exc,
            )
    raise AssertionError("unreachable")
