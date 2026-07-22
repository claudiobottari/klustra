from typing import Any

import pytest

from klustra.core.state_store import (
    CompileCheckpoint,
    HierarchyStateRecord,
    PageRecord,
    SourceRecord,
    StateStore,
)


class InMemoryStateStore(StateStore):
    """Minimal fake used only to exercise the ABC contract in tests."""

    def __init__(self) -> None:
        self._sources: dict[str, SourceRecord] = {}
        self._pages: dict[str, PageRecord] = {}
        self._links: dict[str, list[str]] = {}
        self._runs: list[tuple[str, dict[str, Any]]] = []
        self._hierarchy: HierarchyStateRecord | None = None
        self._checkpoints: dict[str, CompileCheckpoint] = {}

    def get_source(self, source_id: str) -> SourceRecord | None:
        return self._sources.get(source_id)

    def put_source(self, record: SourceRecord, *, run_id: str) -> None:
        self._sources[record.source_id] = record

    def remove_source(self, source_id: str, *, run_id: str) -> None:
        self._sources.pop(source_id, None)

    def list_sources(self) -> list[SourceRecord]:
        return list(self._sources.values())

    def get_page(self, entity_id: str) -> PageRecord | None:
        return self._pages.get(entity_id)

    def put_page(self, record: PageRecord, *, run_id: str) -> None:
        self._pages[record.entity_id] = record

    def remove_page(self, entity_id: str, *, run_id: str) -> None:
        self._pages.pop(entity_id, None)

    def list_pages(self) -> list[PageRecord]:
        return list(self._pages.values())

    def get_links(self, entity_id: str) -> list[str]:
        return self._links.get(entity_id, [])

    def set_links(self, entity_id: str, targets: list[str], *, run_id: str) -> None:
        self._links[entity_id] = targets

    def append_run(self, run_id: str, record: dict[str, Any]) -> None:
        self._runs.append((run_id, record))

    def get_checkpoints(self) -> dict[str, CompileCheckpoint]:
        return dict(self._checkpoints)

    def put_checkpoint(self, record: CompileCheckpoint, *, run_id: str) -> None:
        self._checkpoints[record.source_id] = record

    def clear_checkpoints(self, *, run_id: str) -> None:
        self._checkpoints = {}

    def get_hierarchy_state(self) -> HierarchyStateRecord | None:
        return self._hierarchy

    def put_hierarchy_state(self, record: HierarchyStateRecord, *, run_id: str) -> None:
        self._hierarchy = record


def test_state_store_is_abstract():
    with pytest.raises(TypeError):
        StateStore()  # type: ignore[abstract]


def test_source_roundtrip(now):
    store = InMemoryStateStore()
    record = SourceRecord(
        source_id="sha256:abc",
        source_path="C:/data/file.xlsx",
        translator="excel@1.0",
        created_at=now,
        updated_at=now,
    )
    store.put_source(record, run_id="run-1")
    assert store.get_source("sha256:abc") == record
    assert store.list_sources() == [record]

    store.remove_source("sha256:abc", run_id="run-2")
    assert store.get_source("sha256:abc") is None


def test_page_roundtrip():
    store = InMemoryStateStore()
    record = PageRecord(
        entity_id="prod.cable.p-laser",
        source_ids=["sha256:abc"],
        level=0,
        content_hash="sha256:xyz",
    )
    store.put_page(record, run_id="run-1")
    assert store.get_page("prod.cable.p-laser") == record

    store.remove_page("prod.cable.p-laser", run_id="run-2")
    assert store.get_page("prod.cable.p-laser") is None


def test_links_and_run_log():
    store = InMemoryStateStore()
    assert store.get_links("prod.cable.p-laser") == []

    store.set_links("prod.cable.p-laser", ["prod.family.p-laser"], run_id="run-1")
    assert store.get_links("prod.cable.p-laser") == ["prod.family.p-laser"]

    store.append_run("run-1", {"command": "compile"})
    assert store._runs == [("run-1", {"command": "compile"})]


def test_checkpoint_contract_on_the_abc(now):
    store = InMemoryStateStore()
    assert store.get_checkpoints() == {}

    cp = CompileCheckpoint(
        source_id="src-a", status="done", sha256="h", entity_ids=["a.b"], updated_at=now
    )
    store.put_checkpoint(cp, run_id="run-1")
    assert store.get_checkpoints() == {"src-a": cp}

    store.clear_checkpoints(run_id="run-2")
    assert store.get_checkpoints() == {}
