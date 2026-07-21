from __future__ import annotations

import json

import pytest

from klustra.core.errors import LLMValidationError
from klustra.core.knowledge_unit import KnowledgeUnit
from klustra.engine.librarian import merge_and_generate, persist_librarian_result
from klustra.engine.models import LibrarianResult, SourceContribution
from klustra.llm import MockProvider
from klustra.llm.accounting import ListSink
from klustra.llm.provider import LLMRequest, LLMResponse


def _make_contribution(source_id: str, source_path: str, contents: list[str]) -> SourceContribution:
    units = [
        KnowledgeUnit(
            unit_id=f"{source_id}#{i + 1}",
            kind="narrative",
            content_md=c,
            locator=f"doc:{i + 1}",
        )
        for i, c in enumerate(contents)
    ]
    return SourceContribution(source_id=source_id, source_path=source_path, units=units)


def _canned_librarian_output(
    title: str = "P-Laser 320kV",
    body_md: str = "The P-Laser cable uses XLPE. ^[src001:doc:1]",
    confidence: float = 0.9,
) -> str:
    return json.dumps(
        {
            "title": title,
            "description": "A high-voltage cable product.",
            "body_md": body_md,
            "tags": ["cable", "hv"],
            "aliases": ["P-Laser"],
            "confidence": confidence,
        }
    )


def _provider_with_canned(contributions: list[SourceContribution], response: str) -> MockProvider:
    """Build a MockProvider with the canned response keyed to the expected request."""
    provider = MockProvider(canned={})
    provider._canned = {}

    from klustra.engine.librarian import _build_request
    from klustra.llm.mock_provider import _request_key

    request = _build_request(
        "prod.cable.p-laser-320kv",
        contributions,
        ["mat.xlpe", "proc.extrusion"],
        "test-model",
        None,
    )
    key = _request_key(request)
    provider._canned[key] = response
    return provider


class TestMultiSourceMerge:
    def test_basic_merge(self) -> None:
        contributions = [
            _make_contribution("src001", "/data/a.xlsx", ["P-Laser is a 320kV cable."]),
            _make_contribution("src002", "/data/b.md", ["P-Laser uses XLPE insulation."]),
        ]
        body = (
            "P-Laser is a 320kV cable. ^[src001:doc:1] "
            "It uses XLPE insulation. ^[src002:doc:1] "
            "See [[mat.xlpe]] for material details."
        )
        provider = _provider_with_canned(contributions, _canned_librarian_output(body_md=body))
        sink = ListSink()

        result = merge_and_generate(
            entity_id="prod.cable.p-laser-320kv",
            contributions=contributions,
            existing_index=["mat.xlpe", "proc.extrusion"],
            domain="test",
            provider=provider,
            model="test-model",
            sink=sink,
        )

        assert isinstance(result, LibrarianResult)
        assert result.page.entity_id == "prod.cable.p-laser-320kv"
        assert result.page.title == "P-Laser 320kV"
        assert result.page.domain == "test"
        assert result.page.level == 0
        assert len(result.page.sources) == 2
        assert "mat.xlpe" in result.link_targets
        assert result.body_md == body

    def test_token_accounting(self) -> None:
        contributions = [
            _make_contribution("src001", "/a.md", ["Content."]),
        ]
        provider = _provider_with_canned(contributions, _canned_librarian_output())
        sink = ListSink()

        merge_and_generate(
            entity_id="prod.cable.p-laser-320kv",
            contributions=contributions,
            existing_index=["mat.xlpe", "proc.extrusion"],
            domain="test",
            provider=provider,
            model="test-model",
            sink=sink,
        )

        assert len(sink.entries) >= 1
        assert sink.entries[0].role == "librarian"
        assert sink.entries[0].model == "test-model"

    def test_sources_in_page(self) -> None:
        contributions = [
            _make_contribution("src001", "/data/a.xlsx", ["Info A."]),
            _make_contribution("src002", "/data/b.md", ["Info B."]),
            _make_contribution("src003", "/data/c.txt", ["Info C."]),
        ]
        provider = _provider_with_canned(contributions, _canned_librarian_output())
        sink = ListSink()

        result = merge_and_generate(
            entity_id="prod.cable.p-laser-320kv",
            contributions=contributions,
            existing_index=["mat.xlpe", "proc.extrusion"],
            domain="test",
            provider=provider,
            model="test-model",
            sink=sink,
        )

        source_ids = [s.source_id for s in result.page.sources]
        assert source_ids == ["src001", "src002", "src003"]


class TestConflictResolution:
    def test_obsolescence_in_body(self) -> None:
        """Conflicting claims → most recent wins, old → Storia e revisioni."""
        contributions = [
            _make_contribution("src001", "/old.md", ["Voltage is 220kV."]),
            _make_contribution("src002", "/new.md", ["Voltage is 320kV."]),
        ]
        body = (
            "The cable operates at 320kV. ^[src002:doc:1]\n\n"
            "## Storia e revisioni\n\n"
            "Previously reported as 220kV. ^[src001:doc:1]"
        )
        provider = _provider_with_canned(contributions, _canned_librarian_output(body_md=body))
        sink = ListSink()

        result = merge_and_generate(
            entity_id="prod.cable.p-laser-320kv",
            contributions=contributions,
            existing_index=["mat.xlpe", "proc.extrusion"],
            domain="test",
            provider=provider,
            model="test-model",
            sink=sink,
        )

        assert "## Storia e revisioni" in result.body_md
        assert "^[src001:doc:1]" in result.body_md
        assert "^[src002:doc:1]" in result.body_md


class TestCitationEnforcement:
    def test_no_citations_triggers_retry(self) -> None:
        """First response has no citations → retry → second has citations."""
        contributions = [
            _make_contribution("src001", "/a.md", ["Cable info."]),
        ]
        # MockProvider with schema fallback will produce minimal output without citations.
        # We need to set up so the first call returns no citations,
        # and the second (retry) returns citations.
        # Using a custom provider that tracks call count.

        class _RetryProvider(MockProvider):
            def __init__(self) -> None:
                super().__init__()
                self._call_count = 0

            def call(self, request: LLMRequest) -> LLMResponse:  # type: ignore[override]
                self._call_count += 1
                if self._call_count == 1:
                    content = json.dumps(
                        {
                            "title": "Cable",
                            "description": "A cable.",
                            "body_md": "This is a cable with no citations.",
                            "tags": [],
                            "aliases": [],
                            "confidence": 0.8,
                        }
                    )
                else:
                    content = json.dumps(
                        {
                            "title": "Cable",
                            "description": "A cable.",
                            "body_md": "This is a cable. ^[src001:doc:1]",
                            "tags": [],
                            "aliases": [],
                            "confidence": 0.8,
                        }
                    )
                parsed = json.loads(content)
                return LLMResponse(
                    content=content,
                    parsed=parsed,
                    tokens_in=10,
                    tokens_out=10,
                    model="test-model",
                )

        provider = _RetryProvider()
        sink = ListSink()

        result = merge_and_generate(
            entity_id="prod.cable.p-laser-320kv",
            contributions=contributions,
            existing_index=[],
            domain="test",
            provider=provider,
            model="test-model",
            sink=sink,
        )

        assert "^[src001:doc:1]" in result.body_md
        assert provider._call_count == 2
        assert len(sink.entries) == 2

    def test_no_citations_after_retry_raises(self) -> None:
        """Both attempts produce no citations → LLMValidationError."""
        contributions = [
            _make_contribution("src001", "/a.md", ["Cable info."]),
        ]

        class _AlwaysBadProvider(MockProvider):
            def call(self, request: LLMRequest) -> LLMResponse:  # type: ignore[override]
                content = json.dumps(
                    {
                        "title": "Cable",
                        "description": "A cable.",
                        "body_md": "No citations here at all.",
                        "tags": [],
                        "aliases": [],
                        "confidence": 0.8,
                    }
                )
                parsed = json.loads(content)
                return LLMResponse(
                    content=content,
                    parsed=parsed,
                    tokens_in=10,
                    tokens_out=10,
                    model="test-model",
                )

        provider = _AlwaysBadProvider()
        sink = ListSink()

        with pytest.raises(LLMValidationError, match="no citations"):
            merge_and_generate(
                entity_id="prod.cable.p-laser-320kv",
                contributions=contributions,
                existing_index=[],
                domain="test",
                provider=provider,
                model="test-model",
                sink=sink,
            )


class TestWikilinkResolution:
    def test_resolved_links_in_result(self) -> None:
        contributions = [
            _make_contribution("src001", "/a.md", ["Uses XLPE."]),
        ]
        body = "Uses [[mat.xlpe]] insulation. ^[src001:doc:1]"
        provider = _provider_with_canned(contributions, _canned_librarian_output(body_md=body))
        sink = ListSink()

        result = merge_and_generate(
            entity_id="prod.cable.p-laser-320kv",
            contributions=contributions,
            existing_index=["mat.xlpe", "proc.extrusion"],
            domain="test",
            provider=provider,
            model="test-model",
            sink=sink,
        )

        assert "mat.xlpe" in result.link_targets
        assert "proc.extrusion" not in result.link_targets

    def test_unresolved_links_not_in_targets(self) -> None:
        contributions = [
            _make_contribution("src001", "/a.md", ["Content."]),
        ]
        body = "See [[nonexistent.thing]] for more. ^[src001:doc:1]"
        provider = _provider_with_canned(contributions, _canned_librarian_output(body_md=body))
        sink = ListSink()

        result = merge_and_generate(
            entity_id="prod.cable.p-laser-320kv",
            contributions=contributions,
            existing_index=["mat.xlpe", "proc.extrusion"],
            domain="test",
            provider=provider,
            model="test-model",
            sink=sink,
        )

        assert "nonexistent.thing" not in result.link_targets

    def test_librarian_routes_wikilinks_through_resolver(self) -> None:
        """CLAUDE.md hard rule #2: resolver is the sole component gating link_targets.

        - Valid wikilinks appear in link_targets.
        - Invalid wikilinks are dropped from link_targets.
        - Body markdown is NOT rewritten by librarian (resolver doesn't strip either —
          downstream lint reports unresolved links; librarian passes body through unchanged).
        """
        contributions = [
            _make_contribution("src001", "/a.md", ["Content."]),
        ]
        body = (
            "Uses [[mat.xlpe]] insulation and [[proc.extrusion]] process, "
            "with a broken ref to [[bogus.made-up]]. ^[src001:doc:1]"
        )
        provider = _provider_with_canned(contributions, _canned_librarian_output(body_md=body))
        sink = ListSink()

        result = merge_and_generate(
            entity_id="prod.cable.p-laser-320kv",
            contributions=contributions,
            existing_index=["mat.xlpe", "proc.extrusion"],
            domain="test",
            provider=provider,
            model="test-model",
            sink=sink,
        )

        assert set(result.link_targets) == {"mat.xlpe", "proc.extrusion"}
        assert "bogus.made-up" not in result.link_targets
        assert "[[bogus.made-up]]" in result.body_md
        assert "[[mat.xlpe]]" in result.body_md


class TestPersistResult:
    def test_persist_writes_to_store(self) -> None:
        from unittest.mock import MagicMock

        contributions = [
            _make_contribution("src001", "/a.md", ["Content."]),
        ]
        body = "Cable info. ^[src001:doc:1] See [[mat.xlpe]]."
        provider = _provider_with_canned(contributions, _canned_librarian_output(body_md=body))
        sink = ListSink()

        result = merge_and_generate(
            entity_id="prod.cable.p-laser-320kv",
            contributions=contributions,
            existing_index=["mat.xlpe", "proc.extrusion"],
            domain="test",
            provider=provider,
            model="test-model",
            sink=sink,
        )

        store = MagicMock()
        persist_librarian_result(result, store, run_id="run-123")

        store.put_page.assert_called_once()
        page_record = store.put_page.call_args[0][0]
        assert page_record.entity_id == "prod.cable.p-laser-320kv"
        assert "src001" in page_record.source_ids

        store.set_links.assert_called_once()
        args = store.set_links.call_args
        assert args[0][0] == "prod.cable.p-laser-320kv"
        assert "mat.xlpe" in args[0][1]
