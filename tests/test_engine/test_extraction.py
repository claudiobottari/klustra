from __future__ import annotations

import json
import logging

import pytest

from klustra.core.errors import LLMInputTooLargeError
from klustra.core.knowledge_unit import KnowledgeUnit
from klustra.engine.extraction import extract_concepts
from klustra.llm import MockProvider
from klustra.llm.accounting import ListSink
from klustra.llm.provider import LLMProvider, LLMRequest, LLMResponse
from klustra.llm.tokens import count_tokens


def test_extract_concepts_returns_results(
    mock_provider: MockProvider, sample_units: list[KnowledgeUnit]
) -> None:
    sink = ListSink()
    results = extract_concepts(
        units=sample_units,
        source_id="src001",
        existing_index=["mat.xlpe"],
        provider=mock_provider,
        model="test-model",
        sink=sink,
    )
    assert len(results) == 2
    assert results[0].source_id == "src001"
    assert results[0].unit_id == "src001#1"
    assert results[1].unit_id == "src001#2"


def test_extract_concepts_records_tokens(
    mock_provider: MockProvider, sample_units: list[KnowledgeUnit]
) -> None:
    sink = ListSink()
    extract_concepts(
        units=sample_units,
        source_id="src001",
        existing_index=[],
        provider=mock_provider,
        model="test-model",
        sink=sink,
    )
    assert len(sink.entries) == 2
    assert all(e.role == "extraction" for e in sink.entries)
    assert all(e.model == "test-model" for e in sink.entries)


def test_extract_concepts_with_canned_response() -> None:
    import hashlib

    unit = KnowledgeUnit(
        unit_id="src001#1",
        kind="narrative",
        content_md="P-Laser cable info",
        locator="doc:1",
    )

    canned_output = json.dumps(
        {
            "candidates": [
                {
                    "name": "P-Laser 320kV",
                    "entity_id_proposal": "prod.cable.p-laser-320kv",
                    "summary": "A high-voltage cable.",
                    "is_new": True,
                    "related_existing": [],
                }
            ]
        }
    )

    system = (
        "You are an extraction engine. Given a knowledge unit, identify concept candidates.\n"
        "Return structured JSON with a list of candidates.\n"
        "Each candidate has: name, entity_id_proposal (dot-separated lowercase), "
        "summary, is_new (true if not in existing index), related_existing (entity_ids from index)."
    )
    user = (
        "## Existing entity index\n(empty)\n\n"
        "## Knowledge unit [narrative]\nLocator: doc:1\n\nP-Laser cable info"
    )
    content = system + user
    key = hashlib.sha256(content.encode()).hexdigest()[:16]

    provider = MockProvider(canned={key: canned_output})
    sink = ListSink()

    results = extract_concepts(
        units=[unit],
        source_id="src001",
        existing_index=[],
        provider=provider,
        model="test-model",
        sink=sink,
    )
    assert len(results) == 1
    assert len(results[0].candidates) == 1
    c = results[0].candidates[0]
    assert c.name == "P-Laser 320kV"
    assert c.entity_id_proposal == "prod.cable.p-laser-320kv"
    assert c.is_new is True


class _ContextLimitedProvider(LLMProvider):
    """Rejects oversized input the way a real provider would — so a regression
    that stops chunking fails the test instead of quietly passing."""

    name = "context_limited"

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.requests: list[LLMRequest] = []

    def call(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        total = sum(count_tokens(m.content) for m in request.messages)
        if total > self.limit:
            raise AssertionError(f"provider received {total} tokens, over its {self.limit} limit")

        # One distinct candidate per chunk, plus a shared one to exercise dedup.
        idx = len(self.requests)
        data = {
            "candidates": [
                {
                    "name": f"Concept {idx}",
                    "entity_id_proposal": f"c.part{idx}",
                    "summary": "partial",
                    "is_new": True,
                    "related_existing": [],
                },
                {
                    "name": "Shared Concept",
                    "entity_id_proposal": "c.shared",
                    "summary": "seen in every chunk",
                    "is_new": True,
                    "related_existing": [],
                },
            ]
        }
        content = json.dumps(data)
        return LLMResponse(
            content=content,
            parsed=data,
            tokens_in=total,
            tokens_out=len(content) // 4,
            model=request.model,
        )


def _large_unit(sections: int = 12, words: int = 400) -> KnowledgeUnit:
    body = "\n\n".join(
        f"## Section {i}\n\n" + " ".join(f"term{i}n{j}" for j in range(words))
        for i in range(sections)
    )
    return KnowledgeUnit(unit_id="src001#1", kind="narrative", content_md=body, locator="doc:1")


def test_large_unit_is_chunked_into_multiple_calls(
    caplog: pytest.LogCaptureFixture,
) -> None:
    unit = _large_unit()
    limit = 4000
    assert count_tokens(unit.content_md) > limit, "fixture must actually be oversized"

    provider = _ContextLimitedProvider(limit=limit)
    sink = ListSink()

    with caplog.at_level(logging.INFO, logger="klustra"):
        results = extract_concepts(
            units=[unit],
            source_id="src001",
            existing_index=[],
            provider=provider,
            model="test-model",
            sink=sink,
            max_input_tokens=limit,
        )

    assert len(provider.requests) > 1, "oversized unit must fan out over several calls"
    assert any("chunking triggered" in r.message for r in caplog.records)

    # Reduce step: one ExtractionResult per unit, provenance untouched.
    assert len(results) == 1
    assert results[0].source_id == "src001"
    assert results[0].unit_id == "src001#1"

    # Candidates accumulated across chunks, deduped by entity_id_proposal.
    proposals = [c.entity_id_proposal for c in results[0].candidates]
    assert proposals.count("c.shared") == 1
    assert len([p for p in proposals if p.startswith("c.part")]) == len(provider.requests)

    # Accounting: one record per call, each tagged with the chunk count.
    assert len(sink.entries) == len(provider.requests)
    assert all(e.chunks_used == len(provider.requests) for e in sink.entries)


def test_small_unit_path_is_unchanged(mock_provider: MockProvider) -> None:
    """No chunking for ordinary input: one call, chunks_used stays 1."""
    unit = KnowledgeUnit(
        unit_id="src001#1", kind="narrative", content_md="Short body.", locator="doc:1"
    )
    sink = ListSink()
    extract_concepts(
        units=[unit],
        source_id="src001",
        existing_index=[],
        provider=mock_provider,
        model="test-model",
        sink=sink,
    )
    assert len(sink.entries) == 1
    assert sink.entries[0].chunks_used == 1


def test_scaffolding_over_budget_raises_input_too_large(mock_provider: MockProvider) -> None:
    """Budget so small the prompt itself doesn't fit — a hard error, never a
    blind retry (LLMInputTooLargeError is not an LLMCallError)."""
    from klustra.core.errors import LLMCallError

    assert not issubclass(LLMInputTooLargeError, LLMCallError)

    unit = KnowledgeUnit(unit_id="src001#1", kind="narrative", content_md="body", locator="doc:1")
    with pytest.raises(LLMInputTooLargeError, match="scaffolding"):
        extract_concepts(
            units=[unit],
            source_id="src001",
            existing_index=[],
            provider=mock_provider,
            model="test-model",
            sink=ListSink(),
            max_input_tokens=100,
        )


def test_extract_concepts_empty_units(mock_provider: MockProvider) -> None:
    sink = ListSink()
    results = extract_concepts(
        units=[],
        source_id="src001",
        existing_index=[],
        provider=mock_provider,
        model="test-model",
        sink=sink,
    )
    assert results == []
    assert len(sink.entries) == 0
