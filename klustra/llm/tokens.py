"""Pre-call token counting (SPEC §5.2).

The exact tokenizer of the target provider is usually unavailable (DeepSeek et al.
via OpenRouter expose no local BPE), so cl100k_base is used as a *proxy* and the
result is inflated by SAFETY_MARGIN. For a threshold gate an overestimate is the
safe direction: too high means we chunk earlier than strictly needed, too low
means the call overflows the context window — the bug this guards against.
"""

from __future__ import annotations

import logging
import math
from typing import Any

logger = logging.getLogger(__name__)

SAFETY_MARGIN = 1.20
"""Inflation applied to every count: cl100k is a proxy, not the provider's tokenizer."""

_FALLBACK_CHARS_PER_TOKEN = 3.0
"""Used only when tiktoken is unavailable. Deliberately below the ~4 chars/token
rule of thumb so the fallback also overestimates."""

_encoding_cache: Any | None = None
_encoding_failed = False


def _encoding() -> Any | None:
    """cl100k_base encoding, or None if tiktoken can't be loaded.

    tiktoken downloads the BPE vocabulary on first use; an offline machine must
    degrade to the char heuristic rather than fail the whole compile.
    """
    global _encoding_cache, _encoding_failed
    if _encoding_cache is not None or _encoding_failed:
        return _encoding_cache
    try:
        import tiktoken

        _encoding_cache = tiktoken.get_encoding("cl100k_base")
    except Exception as exc:  # noqa: BLE001 - any failure degrades, never propagates
        _encoding_failed = True
        logger.debug("tiktoken unavailable (%s); using char heuristic for token counts", exc)
    return _encoding_cache


def count_tokens(text: str) -> int:
    """Conservative token count for `text`, including SAFETY_MARGIN."""
    if not text:
        return 0
    enc = _encoding()
    if enc is not None:
        raw = len(enc.encode(text, disallowed_special=()))
    else:
        raw = math.ceil(len(text) / _FALLBACK_CHARS_PER_TOKEN)
    return math.ceil(raw * SAFETY_MARGIN)
