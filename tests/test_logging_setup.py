"""The progress contract (SPEC §13.1): nothing runs silently."""

from __future__ import annotations

import logging
import subprocess
import sys
import threading
import time

import pytest

from klustra.logging_setup import configure_logging, log_op


def _messages(caplog: pytest.LogCaptureFixture, level: int | None = None) -> list[str]:
    return [r.message for r in caplog.records if level is None or r.levelno == level]


def test_log_op_emits_start_then_done_with_elapsed(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="klustra"):
        with log_op("extraction", "llm_call", source_id="src1", chunk="2/5"):
            pass

    msgs = _messages(caplog, logging.INFO)
    assert len(msgs) == 2
    assert msgs[0] == "phase=extraction action=llm_call source_id=src1 chunk=2/5 status=start"
    assert msgs[1].startswith(
        "phase=extraction action=llm_call source_id=src1 chunk=2/5 status=done"
    )
    assert "elapsed_ms=" in msgs[1]


def test_log_op_start_is_emitted_before_the_work_completes(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The whole point: a record must be visible while the operation is still
    running, not only after it returns."""
    seen_mid_flight: list[str] = []

    with caplog.at_level(logging.INFO, logger="klustra"):
        with log_op("hierarchy", "cluster"):
            seen_mid_flight.extend(r.message for r in caplog.records)

    assert any("status=start" in m for m in seen_mid_flight)
    assert not any("status=done" in m for m in seen_mid_flight)


def test_log_op_logs_failure_with_error_type_and_reraises(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger="klustra"):
        with pytest.raises(ValueError):
            with log_op("librarian_merge", "llm_call", entity_id="iec_62067"):
                raise ValueError("boom")

    errors = _messages(caplog, logging.ERROR)
    assert len(errors) == 1
    assert "status=failed" in errors[0]
    assert "error=ValueError" in errors[0]
    assert "entity_id=iec_62067" in errors[0]
    assert "elapsed_ms=" in errors[0]


def test_log_op_never_renders_none_fields(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="klustra"):
        with log_op("export", "write", entity_id=None, count=3):
            pass

    assert "entity_id" not in _messages(caplog)[0]
    assert "count=3" in _messages(caplog)[0]


def test_heartbeat_fires_while_the_caller_is_blocked(caplog: pytest.LogCaptureFixture) -> None:
    """Driven by an injected Event, not wall-clock sleeps — the calling thread is
    blocked, so only a watchdog thread can report progress."""
    released = threading.Event()

    with caplog.at_level(logging.INFO, logger="klustra"):
        with log_op(
            "extraction",
            "llm_call",
            heartbeat=True,
            heartbeat_interval=0.01,
            source_id="src1",
        ):
            # Block until at least one heartbeat has landed.
            deadline = time.monotonic() + 5.0
            while time.monotonic() < deadline:
                if any("status=running" in r.message for r in caplog.records):
                    released.set()
                    break
                time.sleep(0.01)

    assert released.is_set(), "no heartbeat arrived while the operation was in flight"
    beats = [m for m in _messages(caplog) if "status=running" in m]
    assert beats
    assert "elapsed_ms=" in beats[0]
    assert "source_id=src1" in beats[0]


def test_heartbeat_thread_stops_after_the_operation(caplog: pytest.LogCaptureFixture) -> None:
    before = threading.active_count()
    with caplog.at_level(logging.INFO, logger="klustra"):
        with log_op("hierarchy", "umap_reduce", heartbeat=True, heartbeat_interval=0.01):
            pass
    time.sleep(0.1)

    assert threading.active_count() <= before
    assert not any("status=running" in m for m in _messages(caplog))


def test_quiet_suppresses_progress_but_default_shows_it() -> None:
    logger = logging.getLogger("klustra")

    configure_logging()
    assert logger.level == logging.INFO
    configure_logging(quiet=True)
    assert logger.level == logging.WARNING
    configure_logging(verbose=True)
    assert logger.level == logging.DEBUG
    configure_logging()


def test_records_are_flushed_per_line_not_buffered_until_exit() -> None:
    """Regression guard: a handler change that buffers would make a healthy but
    slow run indistinguishable from a hang, even with correct log calls."""
    script = (
        "import logging, time\n"
        "from klustra.logging_setup import configure_logging, log_op\n"
        "configure_logging()\n"
        "with log_op('extraction', 'llm_call', source_id='s1'):\n"
        "    time.sleep(5)\n"
    )
    proc = subprocess.Popen(
        [sys.executable, "-c", script],
        stdout=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    assert proc.stdout is not None
    try:
        started = time.monotonic()
        first = proc.stdout.readline()
        elapsed = time.monotonic() - started
    finally:
        proc.kill()
        proc.wait()

    assert "status=start" in first
    assert elapsed < 4.5, "start line arrived only after the 5s operation finished"
