from __future__ import annotations

import math

import pytest

from klustra.llm import tokens
from klustra.llm.tokens import SAFETY_MARGIN, count_tokens


def test_empty_text_is_zero() -> None:
    assert count_tokens("") == 0


def test_count_includes_safety_margin() -> None:
    text = "The quick brown fox jumps over the lazy dog. " * 20
    enc = tokens._encoding()
    if enc is None:
        pytest.skip("tiktoken unavailable in this environment")
    raw = len(enc.encode(text))
    assert count_tokens(text) == math.ceil(raw * SAFETY_MARGIN)
    assert count_tokens(text) > raw


def test_count_grows_monotonically_with_length() -> None:
    short = "alpha beta gamma"
    long = short * 50
    assert count_tokens(long) > count_tokens(short)


def test_fallback_used_when_tiktoken_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    """An offline machine must degrade to the char heuristic, never crash."""
    monkeypatch.setattr(tokens, "_encoding", lambda: None)
    text = "x" * 300
    expected = math.ceil(math.ceil(300 / tokens._FALLBACK_CHARS_PER_TOKEN) * SAFETY_MARGIN)
    assert count_tokens(text) == expected


def test_fallback_overestimates_relative_to_four_chars_per_token() -> None:
    """The gate wants an overestimate: chunking early is benign, late is the bug."""
    monkeypatch_free_text = "y" * 4000
    naive = len(monkeypatch_free_text) / 4
    assert tokens._FALLBACK_CHARS_PER_TOKEN < 4.0
    assert count_tokens(monkeypatch_free_text) > naive
