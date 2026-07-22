from __future__ import annotations

import pytest
import tenacity

from klustra.core.errors import LLMCallError, LLMRateLimitError, LLMValidationError
from klustra.llm.provider import LLMMessage, LLMRequest, LLMResponse
from klustra.llm.retry import (
    DEFAULT_MAX_ATTEMPTS,
    _max_attempts_for,
    _wait_strategy,
    call_with_corrective_retry,
    find_body_model_ref,
    is_rate_limit_error,
    llm_retry,
)


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


def _request() -> LLMRequest:
    return LLMRequest(
        messages=[LLMMessage(role="user", content="give me json")],
        model="test-model",
        response_schema={"type": "object"},
    )


def _response(content: str) -> LLMResponse:
    return LLMResponse(content=content, parsed={}, tokens_in=1, tokens_out=1, model="test-model")


def test_corrective_retry_succeeds_on_nth_attempt_with_feedback() -> None:
    seen_requests: list[LLMRequest] = []

    def call_fn(req: LLMRequest) -> LLMResponse:
        seen_requests.append(req)
        if len(seen_requests) < 3:
            raise LLMValidationError(
                f"Response is not valid JSON: boom #{len(seen_requests)}",
                raw_content="{'bad': json attempt " + str(len(seen_requests)),
            )
        return _response('{"ok": true}')

    result = call_with_corrective_retry(call_fn, _request(), max_attempts=3)
    assert result.content == '{"ok": true}'
    assert len(seen_requests) == 3

    # First attempt: original request untouched.
    assert seen_requests[0].messages == _request().messages
    # Each retry: original messages + assistant snippet + corrective user message.
    for attempt_idx in (1, 2):
        msgs = seen_requests[attempt_idx].messages
        assert len(msgs) == 3, "retries rebuild from the ORIGINAL request — no message growth"
        assert msgs[1].role == "assistant"
        assert "bad" in msgs[1].content
        assert msgs[2].role == "user"
        assert "REJECTED" in msgs[2].content
        assert f"boom #{attempt_idx}" in msgs[2].content, "feedback carries the LATEST error"
        assert "ONLY valid JSON" in msgs[2].content


def test_corrective_retry_exhausted_raises_last_error() -> None:
    calls = 0

    def call_fn(req: LLMRequest) -> LLMResponse:
        nonlocal calls
        calls += 1
        raise LLMValidationError(f"still bad #{calls}", raw_content="nope")

    with pytest.raises(LLMValidationError, match="still bad #3"):
        call_with_corrective_retry(call_fn, _request(), max_attempts=3)
    assert calls == 3


def test_corrective_retry_does_not_touch_transient_errors() -> None:
    def call_fn(req: LLMRequest) -> LLMResponse:
        raise LLMCallError("network down")

    with pytest.raises(LLMCallError, match="network down"):
        call_with_corrective_retry(call_fn, _request(), max_attempts=3)


# --- retry_attempts wiring + rate-limit backoff differentiation ---


def _fake_state(
    exc: BaseException | None = None,
    *,
    attempt_number: int = 1,
    args: tuple = (),
) -> tenacity.RetryCallState:
    state = tenacity.RetryCallState(retry_object=None, fn=None, args=args, kwargs={})
    state.attempt_number = attempt_number
    if exc is not None:
        state.set_exception((type(exc), exc, None))
    return state


def test_max_attempts_uses_request_retry_attempts() -> None:
    req = LLMRequest(messages=[LLMMessage(role="user", content="x")], model="m", retry_attempts=7)
    state = _fake_state(args=(req,))
    assert _max_attempts_for(state, DEFAULT_MAX_ATTEMPTS) == 7


def test_max_attempts_falls_back_when_request_missing_or_unset() -> None:
    state_no_request = _fake_state()
    assert _max_attempts_for(state_no_request, DEFAULT_MAX_ATTEMPTS) == DEFAULT_MAX_ATTEMPTS

    req = LLMRequest(messages=[LLMMessage(role="user", content="x")], model="m")
    state_unset = _fake_state(args=(req,))
    assert _max_attempts_for(state_unset, DEFAULT_MAX_ATTEMPTS) == DEFAULT_MAX_ATTEMPTS


def test_wait_strategy_rate_limit_gets_longer_backoff_than_default() -> None:
    rate_limit_wait = _wait_strategy(_fake_state(LLMRateLimitError("overloaded")))
    default_wait = _wait_strategy(_fake_state(LLMCallError("boom")))
    assert rate_limit_wait > default_wait
    assert rate_limit_wait >= 2  # _RATE_LIMIT_WAIT min=2
    assert default_wait >= 1  # _DEFAULT_WAIT min=1


def test_is_rate_limit_error_on_status_code() -> None:
    assert is_rate_limit_error(429, None) is True
    assert is_rate_limit_error(500, None) is False


def test_is_rate_limit_error_on_openrouter_provider_error_code() -> None:
    body = {
        "error": {
            "message": "overloaded",
            "metadata": {"provider_error_code": "engine_overloaded"},
        }
    }
    assert is_rate_limit_error(503, body) is True
    assert is_rate_limit_error(503, {"error": {"message": "unrelated"}}) is False


def test_find_body_model_ref_finds_nested_model_key() -> None:
    body = {"error": {"message": "x", "metadata": {"model": "deepseek/deepseek-chat"}}}
    assert find_body_model_ref(body) == "deepseek/deepseek-chat"
    assert find_body_model_ref({"error": {"message": "x"}}) is None
    assert find_body_model_ref(None) is None
