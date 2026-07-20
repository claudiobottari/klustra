from pathlib import Path

import pytest

from klustra.core.errors import SourceNotFoundError, TranslatorNotFoundError
from klustra.core.file_state_store import FileStateStore
from klustra.core.state_store import PageRecord
from klustra.ingestion.source_manager import (
    _source_id,
    ingest_file,
    ingest_folder,
    remove_source,
    sync_folder,
    update_source,
)
from klustra.ingestion.translator_registry import TranslatorRegistry

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _write(path: Path, content: str = "hello") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# ingest_file
# ---------------------------------------------------------------------------


def test_ingest_file_new(
    tmp_path: Path, tmp_state: FileStateStore, registry: TranslatorRegistry
) -> None:
    f = _write(tmp_path / "a.txt")
    cs = ingest_file(f, tmp_state, registry, run_id="r1")
    sid = _source_id(f)
    assert cs.sources.added == [sid]
    assert cs.sources.modified == []
    assert tmp_state.get_source(sid) is not None


def test_ingest_file_unchanged(
    tmp_path: Path, tmp_state: FileStateStore, registry: TranslatorRegistry
) -> None:
    f = _write(tmp_path / "a.txt")
    ingest_file(f, tmp_state, registry, run_id="r1")
    cs = ingest_file(f, tmp_state, registry, run_id="r2")
    assert cs.sources.added == []
    assert cs.sources.modified == []


def test_ingest_file_modified(
    tmp_path: Path, tmp_state: FileStateStore, registry: TranslatorRegistry
) -> None:
    f = _write(tmp_path / "a.txt", "v1")
    ingest_file(f, tmp_state, registry, run_id="r1")
    f.write_text("v2", encoding="utf-8")
    cs = ingest_file(f, tmp_state, registry, run_id="r2")
    assert cs.sources.modified == [_source_id(f)]


def test_ingest_file_unknown_extension_raises(
    tmp_path: Path, tmp_state: FileStateStore, registry: TranslatorRegistry
) -> None:
    f = _write(tmp_path / "a.xlsx")
    with pytest.raises(TranslatorNotFoundError):
        ingest_file(f, tmp_state, registry)


def test_ingest_file_preserves_created_at(
    tmp_path: Path, tmp_state: FileStateStore, registry: TranslatorRegistry
) -> None:
    f = _write(tmp_path / "a.txt", "v1")
    ingest_file(f, tmp_state, registry, run_id="r1")
    r1 = tmp_state.get_source(_source_id(f))
    assert r1 is not None
    f.write_text("v2", encoding="utf-8")
    ingest_file(f, tmp_state, registry, run_id="r2")
    r2 = tmp_state.get_source(_source_id(f))
    assert r2 is not None
    assert r2.created_at == r1.created_at
    assert r2.updated_at >= r1.updated_at


# ---------------------------------------------------------------------------
# ingest_folder
# ---------------------------------------------------------------------------


def test_ingest_folder_recursive(
    tmp_path: Path, tmp_state: FileStateStore, registry: TranslatorRegistry
) -> None:
    _write(tmp_path / "a.txt")
    _write(tmp_path / "sub" / "b.txt")
    cs = ingest_folder(tmp_path, tmp_state, registry, run_id="r1")
    assert len(cs.sources.added) == 2


def test_ingest_folder_non_recursive(
    tmp_path: Path, tmp_state: FileStateStore, registry: TranslatorRegistry
) -> None:
    _write(tmp_path / "a.txt")
    _write(tmp_path / "sub" / "b.txt")
    cs = ingest_folder(tmp_path, tmp_state, registry, run_id="r1", recursive=False)
    assert len(cs.sources.added) == 1


def test_ingest_folder_glob_filter(
    tmp_path: Path, tmp_state: FileStateStore, registry: TranslatorRegistry
) -> None:
    _write(tmp_path / "a.txt")
    _write(tmp_path / "b.md")
    cs = ingest_folder(tmp_path, tmp_state, registry, run_id="r1", glob=["*.txt"])
    assert len(cs.sources.added) == 1
    assert all("a.txt" in tmp_state.get_source(sid).source_path for sid in cs.sources.added)  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# update_source
# ---------------------------------------------------------------------------


def test_update_source_not_found_raises(
    tmp_path: Path, tmp_state: FileStateStore, registry: TranslatorRegistry
) -> None:
    f = _write(tmp_path / "a.txt")
    with pytest.raises(SourceNotFoundError):
        update_source(f, tmp_state, registry)


def test_update_source_modified(
    tmp_path: Path, tmp_state: FileStateStore, registry: TranslatorRegistry
) -> None:
    f = _write(tmp_path / "a.txt", "v1")
    ingest_file(f, tmp_state, registry, run_id="r1")
    f.write_text("v2", encoding="utf-8")
    cs = update_source(f, tmp_state, registry, run_id="r2")
    assert cs.sources.modified == [_source_id(f)]


def test_update_source_unchanged(
    tmp_path: Path, tmp_state: FileStateStore, registry: TranslatorRegistry
) -> None:
    f = _write(tmp_path / "a.txt")
    ingest_file(f, tmp_state, registry, run_id="r1")
    cs = update_source(f, tmp_state, registry, run_id="r2")
    assert cs.sources.modified == []
    assert cs.sources.added == []


# ---------------------------------------------------------------------------
# remove_source
# ---------------------------------------------------------------------------


def test_remove_source_not_found_raises(tmp_path: Path, tmp_state: FileStateStore) -> None:
    f = tmp_path / "ghost.txt"
    f.write_text("x")
    with pytest.raises(SourceNotFoundError):
        remove_source(f, tmp_state)


def test_remove_source_no_pages(
    tmp_path: Path, tmp_state: FileStateStore, registry: TranslatorRegistry
) -> None:
    f = _write(tmp_path / "a.txt")
    ingest_file(f, tmp_state, registry, run_id="r1")
    sid = _source_id(f)
    cs = remove_source(f, tmp_state, run_id="r2")
    assert cs.sources.removed == [sid]
    assert cs.pages.removed == []
    assert cs.pages.affected == []
    assert tmp_state.get_source(sid) is None


def test_remove_source_cascade_zero_sources(
    tmp_path: Path, tmp_state: FileStateStore, registry: TranslatorRegistry
) -> None:
    f = _write(tmp_path / "a.txt")
    ingest_file(f, tmp_state, registry, run_id="r1")
    sid = _source_id(f)
    tmp_state.put_page(
        PageRecord(entity_id="ent-1", source_ids=[sid], level=0, content_hash="abc"),
        run_id="r1",
    )
    cs = remove_source(f, tmp_state, run_id="r2")
    assert "ent-1" in cs.pages.removed
    assert tmp_state.get_page("ent-1") is None


def test_remove_source_cascade_shared_entity(
    tmp_path: Path, tmp_state: FileStateStore, registry: TranslatorRegistry
) -> None:
    f_a = _write(tmp_path / "a.txt")
    f_b = _write(tmp_path / "b.txt")
    ingest_file(f_a, tmp_state, registry, run_id="r1")
    ingest_file(f_b, tmp_state, registry, run_id="r1")
    sid_a = _source_id(f_a)
    sid_b = _source_id(f_b)
    tmp_state.put_page(
        PageRecord(entity_id="ent-shared", source_ids=[sid_a, sid_b], level=0, content_hash="xyz"),
        run_id="r1",
    )
    cs = remove_source(f_a, tmp_state, run_id="r2")
    assert "ent-shared" in cs.pages.affected
    assert "ent-shared" not in cs.pages.removed
    page = tmp_state.get_page("ent-shared")
    assert page is not None
    assert sid_a not in page.source_ids
    assert sid_b in page.source_ids


# ---------------------------------------------------------------------------
# sync_folder
# ---------------------------------------------------------------------------


def test_sync_folder_added(
    tmp_path: Path, tmp_state: FileStateStore, registry: TranslatorRegistry
) -> None:
    _write(tmp_path / "a.txt")
    _write(tmp_path / "b.txt")
    cs = sync_folder(tmp_path, tmp_state, registry, run_id="r1")
    assert len(cs.sources.added) == 2
    assert cs.sources.modified == []
    assert cs.sources.removed == []


def test_sync_folder_modified(
    tmp_path: Path, tmp_state: FileStateStore, registry: TranslatorRegistry
) -> None:
    f = _write(tmp_path / "a.txt", "v1")
    sync_folder(tmp_path, tmp_state, registry, run_id="r1")
    f.write_text("v2", encoding="utf-8")
    cs = sync_folder(tmp_path, tmp_state, registry, run_id="r2")
    assert cs.sources.modified == [_source_id(f)]
    assert cs.sources.added == []
    assert cs.sources.removed == []


def test_sync_folder_removed(
    tmp_path: Path, tmp_state: FileStateStore, registry: TranslatorRegistry
) -> None:
    f = _write(tmp_path / "a.txt")
    sync_folder(tmp_path, tmp_state, registry, run_id="r1")
    sid = _source_id(f)
    f.unlink()
    cs = sync_folder(tmp_path, tmp_state, registry, run_id="r2")
    assert sid in cs.sources.removed
    assert tmp_state.get_source(sid) is None


def test_sync_folder_removed_cascade(
    tmp_path: Path, tmp_state: FileStateStore, registry: TranslatorRegistry
) -> None:
    f = _write(tmp_path / "a.txt")
    sync_folder(tmp_path, tmp_state, registry, run_id="r1")
    sid = _source_id(f)
    tmp_state.put_page(
        PageRecord(entity_id="pg-1", source_ids=[sid], level=0, content_hash="h"),
        run_id="r1",
    )
    f.unlink()
    cs = sync_folder(tmp_path, tmp_state, registry, run_id="r2")
    assert "pg-1" in cs.pages.removed


def test_sync_folder_idempotent(
    tmp_path: Path, tmp_state: FileStateStore, registry: TranslatorRegistry
) -> None:
    _write(tmp_path / "a.txt")
    sync_folder(tmp_path, tmp_state, registry, run_id="r1")
    cs = sync_folder(tmp_path, tmp_state, registry, run_id="r2")
    assert cs.sources.added == []
    assert cs.sources.modified == []
    assert cs.sources.removed == []


def test_sync_folder_glob_filter(
    tmp_path: Path, tmp_state: FileStateStore, registry: TranslatorRegistry
) -> None:
    _write(tmp_path / "a.txt")
    _write(tmp_path / "b.md")
    cs = sync_folder(tmp_path, tmp_state, registry, run_id="r1", glob=["*.txt"])
    assert len(cs.sources.added) == 1
