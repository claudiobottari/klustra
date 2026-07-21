from __future__ import annotations

from klustra.llm.accounting import ListSink, NullSink, TokenRecord


def test_null_sink_accepts_record() -> None:
    sink = NullSink()
    record = TokenRecord(role="extraction", model="m", tokens_in=10, tokens_out=5)
    sink.record(record)


def test_list_sink_stores_records() -> None:
    sink = ListSink()
    r1 = TokenRecord(role="extraction", model="m", tokens_in=100, tokens_out=50)
    r2 = TokenRecord(role="librarian", model="m2", tokens_in=200, tokens_out=80)
    sink.record(r1)
    sink.record(r2)
    assert len(sink.entries) == 2
    assert sink.total_tokens_in == 300
    assert sink.total_tokens_out == 130


def test_token_record_frozen() -> None:
    record = TokenRecord(role="judge", model="x", tokens_in=1, tokens_out=1)
    try:
        record.role = "other"  # type: ignore[misc]
        raise AssertionError("Should not be mutable")
    except Exception:
        pass
