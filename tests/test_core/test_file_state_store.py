import pytest

from klustra.core.errors import StateStoreError
from klustra.core.file_state_store import FileStateStore
from klustra.core.state_store import PageRecord, SourceRecord, StateStore


def _source(now, source_id="sha256:a"):
    return SourceRecord(
        source_id=source_id,
        source_path="C:/data/file.xlsx",
        translator="excel@1.0",
        created_at=now,
        updated_at=now,
    )


def _page(entity_id="prod.cable.p-laser"):
    return PageRecord(
        entity_id=entity_id,
        source_ids=["sha256:a"],
        level=0,
        content_hash="sha256:xyz",
    )


def test_is_a_state_store():
    assert issubclass(FileStateStore, StateStore)


def test_bootstraps_klustra_dir_and_vault(tmp_path):
    FileStateStore(tmp_path)
    assert (tmp_path / ".klustra").is_dir()
    assert (tmp_path / ".klustra" / "vault").is_dir()


def test_constructing_twice_on_same_root_is_safe(tmp_path):
    FileStateStore(tmp_path)
    FileStateStore(tmp_path)  # must not raise


def test_put_source_persists_and_stamps_run_id(tmp_path, now):
    store = FileStateStore(tmp_path)
    record = _source(now)
    store.put_source(record, run_id="run-1")

    assert store.get_source("sha256:a") == record
    runs = store.list_runs()
    assert len(runs) == 1
    assert runs[0].run_id == "run-1"
    assert runs[0].record["op"] == "put_source"
    assert (tmp_path / ".klustra" / "state.json").exists()


def test_put_source_is_idempotent(tmp_path, now):
    store = FileStateStore(tmp_path)
    record = _source(now)
    store.put_source(record, run_id="run-1")
    store.put_source(record, run_id="run-1")

    assert store.list_sources() == [record]
    assert len(store.list_runs()) == 1


def test_remove_source_idempotent(tmp_path, now):
    store = FileStateStore(tmp_path)
    store.put_source(_source(now), run_id="run-1")
    store.remove_source("sha256:a", run_id="run-2")
    store.remove_source("sha256:a", run_id="run-2")

    assert store.get_source("sha256:a") is None
    assert len(store.list_runs()) == 2


def test_put_page_is_idempotent_and_stamps_run_id(tmp_path):
    store = FileStateStore(tmp_path)
    record = _page()
    store.put_page(record, run_id="run-1")
    store.put_page(record, run_id="run-1")

    assert store.list_pages() == [record]
    runs = [r for r in store.list_runs() if r.record["op"] == "put_page"]
    assert len(runs) == 1
    assert runs[0].run_id == "run-1"


def test_remove_page_idempotent(tmp_path):
    store = FileStateStore(tmp_path)
    store.put_page(_page(), run_id="run-1")
    store.remove_page("prod.cable.p-laser", run_id="run-2")
    store.remove_page("prod.cable.p-laser", run_id="run-2")

    assert store.get_page("prod.cable.p-laser") is None
    assert len(store.list_runs()) == 2


def test_set_links_idempotent_and_stamps_run_id(tmp_path):
    store = FileStateStore(tmp_path)
    store.set_links("prod.cable.p-laser", ["prod.family.p-laser"], run_id="run-1")
    store.set_links("prod.cable.p-laser", ["prod.family.p-laser"], run_id="run-1")

    assert store.get_links("prod.cable.p-laser") == ["prod.family.p-laser"]
    assert len(store.list_runs()) == 1
    assert store.list_runs()[0].run_id == "run-1"


def test_get_links_missing_entity_returns_empty_list(tmp_path):
    store = FileStateStore(tmp_path)
    assert store.get_links("unknown.entity") == []


def test_append_run_stamps_and_is_idempotent(tmp_path):
    store = FileStateStore(tmp_path)
    store.append_run("run-1", {"command": "compile"})
    store.append_run("run-1", {"command": "compile"})

    runs = store.list_runs()
    assert len(runs) == 1
    assert runs[0].run_id == "run-1"
    assert runs[0].record == {"command": "compile"}


def test_append_run_distinct_records_both_kept(tmp_path):
    store = FileStateStore(tmp_path)
    store.append_run("run-1", {"command": "compile"})
    store.append_run("run-1", {"command": "hierarchy"})

    assert len(store.list_runs()) == 2


def test_state_survives_reload_from_disk(tmp_path, now):
    store = FileStateStore(tmp_path)
    source = _source(now)
    page = _page()
    store.put_source(source, run_id="run-1")
    store.put_page(page, run_id="run-1")
    store.set_links("prod.cable.p-laser", ["prod.family.p-laser"], run_id="run-1")
    store.append_run("run-1", {"command": "compile"})

    reloaded = FileStateStore(tmp_path)

    assert reloaded.get_source("sha256:a") == source
    assert reloaded.get_page("prod.cable.p-laser") == page
    assert reloaded.get_links("prod.cable.p-laser") == ["prod.family.p-laser"]
    assert len(reloaded.list_runs()) == len(store.list_runs())
    assert reloaded.list_runs() == store.list_runs()


def test_corrupt_state_file_raises_state_store_error(tmp_path):
    klustra_dir = tmp_path / ".klustra"
    klustra_dir.mkdir()
    (klustra_dir / "state.json").write_text("not valid json {{{", encoding="utf-8")

    with pytest.raises(StateStoreError):
        FileStateStore(tmp_path)


def test_flush_does_not_leave_temp_files_behind(tmp_path, now):
    store = FileStateStore(tmp_path)
    store.put_source(_source(now), run_id="run-1")

    klustra_dir = tmp_path / ".klustra"
    leftovers = [p for p in klustra_dir.iterdir() if p.name.endswith(".tmp")]
    assert leftovers == []
