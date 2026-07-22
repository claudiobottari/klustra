"""Logging configuration and the pipeline's progress contract (SPEC §13.1).

CLI wiring lives here (`configure_logging`); `log_op` is the one helper every
long-running or LLM-touching operation uses so nothing runs silently.
"""

from __future__ import annotations

import logging
import sys
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

_LOGGER_NAME = "klustra"
_PROGRESS_FORMAT = "%(message)s"
_DEBUG_FORMAT = "%(asctime)s %(name)s %(levelname)s %(message)s"

HEARTBEAT_INTERVAL_SECONDS = 15.0
"""How often a long single blocking operation reports it is still alive."""

_op_logger = logging.getLogger("klustra.progress")


def configure_logging(*, verbose: bool = False, quiet: bool = False) -> None:
    """Configure the 'klustra' logger tree for CLI output.

    INFO (default): progress lines ([compile]/[hierarchy]/[sync]/[export]).
    WARNING (--quiet): retries only ([llm] ...), no progress lines.
    DEBUG (--verbose): request/response shapes and full token counts — never
    full prompt/output content (CLAUDE.md: never log contents/prompts), only
    bounded snippets.
    """
    level = logging.DEBUG if verbose else logging.WARNING if quiet else logging.INFO
    fmt = _DEBUG_FORMAT if verbose else _PROGRESS_FORMAT

    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(level)
    logger.handlers.clear()
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(logging.Formatter(fmt))
    logger.addHandler(handler)


def _fields(pairs: dict[str, Any]) -> str:
    """Render key=value fields. Values are ids, counts and timings only — never
    prompt or response content (CLAUDE.md rule 8)."""
    return " ".join(f"{k}={v}" for k, v in pairs.items() if v is not None)


@contextmanager
def log_op(
    phase: str,
    action: str,
    *,
    heartbeat: bool = False,
    heartbeat_interval: float = HEARTBEAT_INTERVAL_SECONDS,
    _stop_event: threading.Event | None = None,
    **fields: Any,
) -> Iterator[None]:
    """Log start/done/failed with elapsed_ms around one unit of work (SPEC §13.1).

    `phase` is extraction|librarian_merge|hierarchy|export|llm, `action` is
    token_count_check|chunking|llm_call|merge|cluster|embed|... Extra keyword
    fields (entity_id, source_id, chunk, attempt, ...) are rendered as
    key=value.

    `heartbeat=True` starts a daemon thread that reports elapsed time while the
    caller is blocked. Required for synchronous network calls and clustering:
    the calling thread cannot log while it is inside a blocking `create()`.
    """
    prefix = _fields({"phase": phase, "action": action, **fields})
    _op_logger.info("%s status=start", prefix)

    stop = _stop_event if _stop_event is not None else threading.Event()
    started = time.monotonic()
    thread: threading.Thread | None = None

    if heartbeat:

        def _beat() -> None:
            while not stop.wait(heartbeat_interval):
                _op_logger.info(
                    "%s status=running elapsed_ms=%d",
                    prefix,
                    int((time.monotonic() - started) * 1000),
                )

        thread = threading.Thread(target=_beat, daemon=True, name=f"heartbeat-{phase}-{action}")
        thread.start()

    try:
        yield
    except BaseException as exc:
        _op_logger.error(
            "%s status=failed elapsed_ms=%d error=%s",
            prefix,
            int((time.monotonic() - started) * 1000),
            type(exc).__name__,
        )
        raise
    else:
        _op_logger.info(
            "%s status=done elapsed_ms=%d",
            prefix,
            int((time.monotonic() - started) * 1000),
        )
    finally:
        stop.set()
        if thread is not None:
            thread.join(timeout=1.0)
