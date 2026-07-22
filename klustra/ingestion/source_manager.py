"""Source manager — file discovery, tracking, and cascade delete (SPEC §4.3)."""

import fnmatch
import hashlib
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

from klustra.core.changeset import ChangeSet, PageChanges, SourceChanges
from klustra.core.errors import SourceNotFoundError
from klustra.core.state_store import PageRecord, SourceRecord, StateStore
from klustra.ingestion.translator_registry import TranslatorRegistry

logger = logging.getLogger(__name__)


def _source_id(path: Path) -> str:
    """Deterministic source_id: first 16 hex chars of SHA-256 of the resolved absolute path."""
    return hashlib.sha256(str(path.resolve()).encode()).hexdigest()[:16]


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _list_folder_files(
    folder: Path,
    recursive: bool,
    glob_patterns: list[str] | None,
) -> list[Path]:
    if recursive:
        candidates = [p for p in folder.rglob("*") if p.is_file()]
    else:
        candidates = [p for p in folder.iterdir() if p.is_file()]
    if not glob_patterns:
        return candidates
    return [p for p in candidates if any(fnmatch.fnmatch(p.name, pat) for pat in glob_patterns)]


def _cascade_remove(
    source_id: str,
    state: StateStore,
    run_id: str,
) -> tuple[list[str], list[str]]:
    """Remove a source and cascade to pages.  Returns (removed_page_ids, affected_page_ids)."""
    removed_pages: list[str] = []
    affected_pages: list[str] = []

    for page in state.list_pages():
        if source_id not in page.source_ids:
            continue
        new_ids = [sid for sid in page.source_ids if sid != source_id]
        if not new_ids:
            state.remove_page(page.entity_id, run_id=run_id)
            removed_pages.append(page.entity_id)
        else:
            updated = PageRecord(
                entity_id=page.entity_id,
                source_ids=new_ids,
                level=page.level,
                content_hash=page.content_hash,
                embedding_hash=page.embedding_hash,
            )
            state.put_page(updated, run_id=run_id)
            affected_pages.append(page.entity_id)

    state.remove_source(source_id, run_id=run_id)
    return removed_pages, affected_pages


def ingest_file(
    path: Path | str,
    state: StateStore,
    registry: TranslatorRegistry,
    *,
    run_id: str | None = None,
) -> ChangeSet:
    """Add or update a single file in state. Raises TranslatorNotFoundError if unregistered."""
    path = Path(path).resolve()
    run_id = run_id or str(uuid.uuid4())
    source_id = _source_id(path)
    sha256 = _file_sha256(path)
    translator_name = registry.get_for_path(path).name

    existing = state.get_source(source_id)
    now = datetime.now(UTC)
    record = SourceRecord(
        source_id=source_id,
        source_path=str(path),
        sha256=sha256,
        translator=translator_name,
        status="active",
        created_at=existing.created_at if existing else now,
        updated_at=now,
    )
    state.put_source(record, run_id=run_id)

    if existing is None:
        return ChangeSet(sources=SourceChanges(added=[source_id]))
    if existing.sha256 != sha256:
        return ChangeSet(sources=SourceChanges(modified=[source_id]))
    return ChangeSet()


def ingest_folder(
    folder: Path | str,
    state: StateStore,
    registry: TranslatorRegistry,
    *,
    run_id: str | None = None,
    recursive: bool = True,
    glob: list[str] | None = None,
) -> ChangeSet:
    """Add or update all matching files in a folder. Does not detect removals."""
    run_id = run_id or str(uuid.uuid4())
    folder = Path(folder).resolve()
    files = [f for f in _list_folder_files(folder, recursive, glob) if registry.can_handle(f)]

    added: list[str] = []
    modified: list[str] = []
    total = len(files)
    for idx, f in enumerate(files, start=1):
        logger.info("[ingest] %d/%d: %s", idx, total, f)
        cs = ingest_file(f, state, registry, run_id=run_id)
        added.extend(cs.sources.added)
        modified.extend(cs.sources.modified)

    return ChangeSet(sources=SourceChanges(added=added, modified=modified))


def update_source(
    path: Path | str,
    state: StateStore,
    registry: TranslatorRegistry,
    *,
    run_id: str | None = None,
) -> ChangeSet:
    """Re-hash an already-tracked file.  Raises SourceNotFoundError if not yet ingested."""
    path = Path(path).resolve()
    source_id = _source_id(path)
    if state.get_source(source_id) is None:
        raise SourceNotFoundError(source_id)
    return ingest_file(path, state, registry, run_id=run_id)


def remove_source(
    path: Path | str,
    state: StateStore,
    *,
    run_id: str | None = None,
) -> ChangeSet:
    """Remove a source and cascade to pages (shared entity preservation, SPEC §4.3)."""
    path = Path(path).resolve()
    run_id = run_id or str(uuid.uuid4())
    source_id = _source_id(path)
    if state.get_source(source_id) is None:
        raise SourceNotFoundError(source_id)
    removed_pages, affected_pages = _cascade_remove(source_id, state, run_id)
    return ChangeSet(
        sources=SourceChanges(removed=[source_id]),
        pages=PageChanges(removed=removed_pages, affected=affected_pages),
    )


def sync_folder(
    folder: Path | str,
    state: StateStore,
    registry: TranslatorRegistry,
    *,
    run_id: str | None = None,
    recursive: bool = True,
    glob: list[str] | None = None,
) -> ChangeSet:
    """Diff on-disk listing vs StateStore state → add/update/remove ChangeSet (SPEC §4.3)."""
    run_id = run_id or str(uuid.uuid4())
    folder = Path(folder).resolve()
    files = [f for f in _list_folder_files(folder, recursive, glob) if registry.can_handle(f)]

    logger.info("[sync] hashing %d file(s) in %s", len(files), folder)

    # Build disk map: source_id → (path, sha256)
    disk_map: dict[str, tuple[Path, str]] = {}
    total = len(files)
    for idx, f in enumerate(files, start=1):
        logger.info("[sync] hashing %d/%d: %s", idx, total, f)
        sid = _source_id(f)
        disk_map[sid] = (f, _file_sha256(f))

    # State records that belong to this folder
    state_map: dict[str, SourceRecord] = {
        r.source_id: r for r in state.list_sources() if Path(r.source_path).is_relative_to(folder)
    }

    added_ids: list[str] = []
    modified_ids: list[str] = []
    removed_page_ids: list[str] = []
    affected_page_ids: list[str] = []

    for sid, (path, sha256) in disk_map.items():
        if sid not in state_map:
            translator_name = registry.get_for_path(path).name
            now = datetime.now(UTC)
            state.put_source(
                SourceRecord(
                    source_id=sid,
                    source_path=str(path),
                    sha256=sha256,
                    translator=translator_name,
                    status="active",
                    created_at=now,
                    updated_at=now,
                ),
                run_id=run_id,
            )
            added_ids.append(sid)
        elif state_map[sid].sha256 != sha256:
            old = state_map[sid]
            state.put_source(
                SourceRecord(
                    source_id=sid,
                    source_path=str(path),
                    sha256=sha256,
                    translator=old.translator or registry.get_for_path(path).name,
                    status="active",
                    created_at=old.created_at,
                    updated_at=datetime.now(UTC),
                ),
                run_id=run_id,
            )
            modified_ids.append(sid)

    for sid in state_map:
        if sid not in disk_map:
            rp, ap = _cascade_remove(sid, state, run_id)
            removed_page_ids.extend(rp)
            affected_page_ids.extend(ap)

    logger.info(
        "[sync] done: +%d ~%d -%d source(s)",
        len(added_ids),
        len(modified_ids),
        len(state_map.keys() - disk_map.keys()),
    )
    return ChangeSet(
        sources=SourceChanges(
            added=added_ids,
            modified=modified_ids,
            removed=list(state_map.keys() - disk_map.keys()),
        ),
        pages=PageChanges(removed=removed_page_ids, affected=affected_page_ids),
    )
