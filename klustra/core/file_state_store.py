import os
import tempfile
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from klustra.core.errors import StateStoreError
from klustra.core.state_store import HierarchyStateRecord, PageRecord, SourceRecord, StateStore


class RunLogEntry(BaseModel):
    """One run-log entry — every mutation stamps its run_id (SPEC §3.2)."""

    model_config = ConfigDict(frozen=True)

    run_id: str
    record: dict[str, Any]


class _StateDocument(BaseModel):
    sources: dict[str, SourceRecord] = Field(default_factory=dict)
    pages: dict[str, PageRecord] = Field(default_factory=dict)
    links: dict[str, list[str]] = Field(default_factory=dict)
    runs: list[RunLogEntry] = Field(default_factory=list)
    hierarchy: HierarchyStateRecord | None = None


class FileStateStore(StateStore):
    """v0.1 StateStore: `.klustra/state.json` backing store + vault directory (SPEC §3.2)."""

    def __init__(self, root: Path | str = Path(".")) -> None:
        self.root = Path(root)
        self.klustra_dir = self.root / ".klustra"
        self.state_path = self.klustra_dir / "state.json"
        self.vault_dir = self.klustra_dir / "vault"
        self.klustra_dir.mkdir(parents=True, exist_ok=True)
        self.vault_dir.mkdir(parents=True, exist_ok=True)
        self._doc = self._load()

    def _load(self) -> _StateDocument:
        if not self.state_path.exists():
            return _StateDocument()
        try:
            text = self.state_path.read_text(encoding="utf-8")
            return _StateDocument.model_validate_json(text)
        except ValidationError as exc:
            raise StateStoreError(f"{self.state_path}: corrupt state file: {exc}") from exc

    def _flush(self) -> None:
        data = self._doc.model_dump_json(indent=2)
        fd, tmp_name = tempfile.mkstemp(dir=self.klustra_dir, prefix="state.", suffix=".tmp")
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(data)
            # Windows: another process (antivirus, indexer) may briefly hold a handle to
            # the freshly-written tmp file, causing os.replace to raise PermissionError.
            last_err: OSError | None = None
            for attempt in range(5):
                try:
                    tmp_path.replace(self.state_path)
                    return
                except PermissionError as exc:
                    last_err = exc
                    time.sleep(0.02 * (2**attempt))
            if last_err is not None:
                raise last_err
        except BaseException:
            tmp_path.unlink(missing_ok=True)
            raise

    def _log(self, run_id: str, op: str, **details: Any) -> None:
        entry = RunLogEntry(run_id=run_id, record={"op": op, **details})
        if entry not in self._doc.runs:
            self._doc.runs.append(entry)

    def get_source(self, source_id: str) -> SourceRecord | None:
        return self._doc.sources.get(source_id)

    def put_source(self, record: SourceRecord, *, run_id: str) -> None:
        self._doc.sources[record.source_id] = record
        self._log(run_id, "put_source", source_id=record.source_id)
        self._flush()

    def remove_source(self, source_id: str, *, run_id: str) -> None:
        self._doc.sources.pop(source_id, None)
        self._log(run_id, "remove_source", source_id=source_id)
        self._flush()

    def list_sources(self) -> list[SourceRecord]:
        return list(self._doc.sources.values())

    def get_page(self, entity_id: str) -> PageRecord | None:
        return self._doc.pages.get(entity_id)

    def put_page(self, record: PageRecord, *, run_id: str) -> None:
        self._doc.pages[record.entity_id] = record
        self._log(run_id, "put_page", entity_id=record.entity_id)
        self._flush()

    def remove_page(self, entity_id: str, *, run_id: str) -> None:
        self._doc.pages.pop(entity_id, None)
        self._log(run_id, "remove_page", entity_id=entity_id)
        self._flush()

    def list_pages(self) -> list[PageRecord]:
        return list(self._doc.pages.values())

    def get_links(self, entity_id: str) -> list[str]:
        return list(self._doc.links.get(entity_id, []))

    def set_links(self, entity_id: str, targets: list[str], *, run_id: str) -> None:
        self._doc.links[entity_id] = list(targets)
        self._log(run_id, "set_links", entity_id=entity_id, targets=list(targets))
        self._flush()

    def append_run(self, run_id: str, record: dict[str, Any]) -> None:
        entry = RunLogEntry(run_id=run_id, record=record)
        if entry not in self._doc.runs:
            self._doc.runs.append(entry)
            self._flush()

    def list_runs(self) -> list[RunLogEntry]:
        """Not part of the StateStore ABC — the ABC has no run-log reader."""
        return list(self._doc.runs)

    def get_hierarchy_state(self) -> HierarchyStateRecord | None:
        return self._doc.hierarchy

    def put_hierarchy_state(self, record: HierarchyStateRecord, *, run_id: str) -> None:
        self._doc.hierarchy = record
        self._log(run_id, "put_hierarchy_state", record_run_id=record.run_id)
        self._flush()
