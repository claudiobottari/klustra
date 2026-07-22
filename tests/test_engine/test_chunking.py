from __future__ import annotations

import logging

import pytest

from klustra.engine.chunking import chunk_text


def _words(text: str) -> int:
    """Deterministic stand-in counter: 1 token per whitespace-separated word."""
    return len(text.split())


def test_under_threshold_returns_input_unchanged() -> None:
    text = "# Title\n\nSome short body.\n\n## Section\n\nMore body."
    assert chunk_text(text, max_tokens=1000, counter=_words) == [text]


def test_rejects_non_positive_budget() -> None:
    with pytest.raises(ValueError, match="must be positive"):
        chunk_text("anything", max_tokens=0, counter=_words)


def test_splits_on_headings_and_never_mid_paragraph() -> None:
    paragraphs = [
        f"## Section {i}\n\n" + " ".join(f"w{i}x{j}" for j in range(20)) for i in range(6)
    ]
    text = "\n\n".join(paragraphs)

    chunks = chunk_text(text, max_tokens=50, counter=_words)

    assert len(chunks) > 1
    for chunk in chunks:
        assert _words(chunk) <= 50
    # No paragraph was cut in half: every original body survives intact somewhere.
    joined = "\n\n".join(chunks)
    for i in range(6):
        body = " ".join(f"w{i}x{j}" for j in range(20))
        assert body in joined


def test_chunks_carry_previous_heading_as_context() -> None:
    text = (
        "## Big Section\n\n"
        + " ".join(f"a{j}" for j in range(30))
        + "\n\n"
        + " ".join(f"b{j}" for j in range(30))
    )
    chunks = chunk_text(text, max_tokens=40, counter=_words)
    assert len(chunks) == 2
    assert "## Big Section" in chunks[0]
    assert "## Big Section (continued)" in chunks[1]


def test_plain_text_splits_on_blank_lines() -> None:
    text = "\n\n".join(" ".join(f"p{i}w{j}" for j in range(15)) for i in range(5))
    chunks = chunk_text(text, max_tokens=35, counter=_words)
    assert len(chunks) > 1
    for chunk in chunks:
        assert _words(chunk) <= 35


def test_oversized_single_paragraph_falls_back_to_sentences_with_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    sentences = [" ".join(f"s{i}w{j}" for j in range(20)) + "." for i in range(5)]
    text = " ".join(sentences)  # one paragraph, no blank lines

    with caplog.at_level(logging.WARNING, logger="klustra"):
        chunks = chunk_text(text, max_tokens=45, counter=_words)

    assert len(chunks) > 1
    for chunk in chunks:
        assert _words(chunk) <= 45
    assert any("sentence-level split" in r.message for r in caplog.records)


def test_oversized_single_sentence_hard_splits_with_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    text = " ".join(f"w{j}" for j in range(200))  # no sentence terminators at all

    with caplog.at_level(logging.WARNING, logger="klustra"):
        chunks = chunk_text(text, max_tokens=30, counter=_words)

    assert len(chunks) > 1
    for chunk in chunks:
        assert _words(chunk) <= 30
    assert any("hard character split" in r.message for r in caplog.records)


def test_every_chunk_respects_budget_with_real_counter() -> None:
    """Exercise the production counter (tiktoken or fallback), not just _words."""
    text = "\n\n".join(
        f"## Heading {i}\n\n" + ("lorem ipsum dolor sit amet " * 40) for i in range(8)
    )
    from klustra.llm.tokens import count_tokens

    chunks = chunk_text(text, max_tokens=400)
    assert len(chunks) > 1
    for chunk in chunks:
        assert count_tokens(chunk) <= 400
