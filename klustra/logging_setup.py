"""CLI logging configuration. CLI-layer + logging-layer only — no api.py return-value
changes; library callers wanting the same visibility from non-CLI contexts is a
separate future concern (see CLAUDE.md)."""

from __future__ import annotations

import logging
import sys

_LOGGER_NAME = "klustra"
_PROGRESS_FORMAT = "%(message)s"
_DEBUG_FORMAT = "%(asctime)s %(name)s %(levelname)s %(message)s"


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
