from __future__ import annotations

import pytest

from klustra.core.errors import LLMCallError, LLMValidationError
from klustra.llm.provider import LLMMessage, LLMRequest, LLMResponse
from klustra.llm.retry import DEFAULT_MAX_ATTEMPTS, call_with_corrective_retry, llm_retry


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
