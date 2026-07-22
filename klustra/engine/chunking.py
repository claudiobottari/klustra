"""Structure-aware text chunking for oversized Phase 1 input (SPEC §5.2).

Deterministic, zero LLM calls. Generic over any KnowledgeUnit content — the
translators all funnel through markdown/plain text before extraction, so this
lives here rather than in any one translator.

Split ladder, applied only as far as needed:
  1. blocks   — markdown headings start a block; otherwise blank-line paragraphs
  2. sentences — only for a single block that overflows on its own (warned)
  3. hard      — character slice, only for a single sentence that overflows (warned)
"""

from __future__ import annotations

import logging
import math
import re
from collections.abc import Callable

from klustra.llm.tokens import count_tokens

logger = logging.getLogger(__name__)

_HEADING_RE = re.compile(r"^#{1,6} ", re.MULTILINE)
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")

TokenCounter = Callable[[str], int]


def chunk_text(
    text: str,
    max_tokens: int,
    counter: TokenCounter = count_tokens,
) -> list[str]:
    """Split `text` into chunks each within `max_tokens`.

    Returns `[text]` unchanged when it already fits — the common path must stay
    byte-identical to the pre-chunking behavior.
    """
    if max_tokens <= 0:
        raise ValueError(f"max_tokens must be positive, got {max_tokens}")
    if counter(text) <= max_tokens:
        return [text]

    blocks = _split_blocks(text)
    chunks: list[str] = []
    current: list[str] = []
    current_heading: str | None = None
    pending_heading: str | None = None

    def flush() -> None:
        nonlocal current, pending_heading
        if current:
            chunks.append("\n\n".join(current))
            pending_heading = current_heading
            current = []

    for block in blocks:
        if _is_heading_block(block):
            current_heading = block.split("\n", 1)[0].strip()

        prefix = ""
        if not current and pending_heading and not _is_heading_block(block):
            prefix = f"{pending_heading} (continued)\n\n"

        candidate = current + [prefix + block]
        if counter("\n\n".join(candidate)) <= max_tokens:
            current = candidate
            continue

        flush()
        piece = (f"{pending_heading} (continued)\n\n" if pending_heading else "") + block
        if counter(piece) <= max_tokens:
            current = [piece]
        else:
            chunks.extend(_split_oversized_block(block, max_tokens, counter))
            pending_heading = current_heading

    flush()
    return [c for c in chunks if c.strip()]


def _split_blocks(text: str) -> list[str]:
    """Paragraph blocks, with every markdown heading forced to start a new block."""
    blocks: list[str] = []
    for para in re.split(r"\n\s*\n", text):
        para = para.strip("\n")
        if not para.strip():
            continue
        # A paragraph may itself contain headings (heading immediately followed
        # by its text with no blank line) — cut before each one.
        starts = [m.start() for m in _HEADING_RE.finditer(para)]
        if not starts or starts == [0]:
            blocks.append(para)
            continue
        bounds = sorted({0, *starts, len(para)})
        for a, b in zip(bounds, bounds[1:], strict=True):
            segment = para[a:b].strip("\n")
            if segment.strip():
                blocks.append(segment)
    return blocks


def _is_heading_block(block: str) -> bool:
    return block.lstrip().startswith("#")


def _split_oversized_block(
    block: str,
    max_tokens: int,
    counter: TokenCounter,
) -> list[str]:
    """A single block exceeds the budget on its own — rare, never silent."""
    logger.warning(
        "[chunking] single block exceeds max_input_tokens (%d > %d); "
        "falling back to sentence-level split",
        counter(block),
        max_tokens,
    )
    return _pack(_split_sentences(block, max_tokens, counter), max_tokens, counter, sep=" ")


def _split_sentences(block: str, max_tokens: int, counter: TokenCounter) -> list[str]:
    pieces: list[str] = []
    for sentence in _SENTENCE_RE.split(block):
        if not sentence.strip():
            continue
        if counter(sentence) <= max_tokens:
            pieces.append(sentence)
            continue
        logger.warning(
            "[chunking] single sentence exceeds max_input_tokens (%d > %d); "
            "falling back to hard character split",
            counter(sentence),
            max_tokens,
        )
        pieces.extend(_split_hard(sentence, max_tokens, counter))
    return pieces


def _split_hard(text: str, max_tokens: int, counter: TokenCounter) -> list[str]:
    """Last resort: slice on characters, shrinking until each slice fits."""
    chars = max(1, math.floor(len(text) * max_tokens / max(1, counter(text))))
    while chars > 1:
        slices = [text[i : i + chars] for i in range(0, len(text), chars)]
        if all(counter(s) <= max_tokens for s in slices):
            return slices
        chars //= 2
    return [text[i : i + 1] for i in range(len(text))]


def _pack(pieces: list[str], max_tokens: int, counter: TokenCounter, sep: str) -> list[str]:
    """Greedily join pieces (each already within budget) into maximal chunks."""
    chunks: list[str] = []
    current: list[str] = []
    for piece in pieces:
        candidate = current + [piece]
        if current and counter(sep.join(candidate)) > max_tokens:
            chunks.append(sep.join(current))
            current = [piece]
        else:
            current = candidate
    if current:
        chunks.append(sep.join(current))
    return chunks
