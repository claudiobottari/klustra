from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

SourceStatus = Literal["active", "removed"]

CheckpointStatus = Literal["pending", "in_progress", "done", "failed"]


class SourceRecord(BaseModel):
    """Tracked source state (SPEC §3.2): SHA-256, path, translator, status, timestamps."""

    model_config = ConfigDict(frozen=True)

    source_id: str
    source_path: str
    sha256: str = ""
    translator: str | None = None
    status: SourceStatus = "active"
    created_at: datetime
    updated_at: datetime


class PageRecord(BaseModel):
    """Tracked page state (SPEC §3.2): entity_id -> source_ids, level, content/embedding hashes."""

    model_config = ConfigDict(frozen=True)

    entity_id: str
    source_ids: list[str] = Field(default_factory=list)
    level: int = Field(ge=0)
    content_hash: str
    embedding_hash: str | None = None
    title: str = ""
    description: str = ""
    tags: list[str] = Field(default_factory=list)


class CompileCheckpoint(BaseModel):
    """Per-source Phase 1 progress for a resumable compile (SPEC §5.3).

    Keyed by `source_id`, NOT `entity_id`: entity_ids are a Phase 1 *output*
    (LLM-proposed, many-to-many with files), so they cannot identify a file
    whose extraction has not run yet.

    `entity_ids` holds the checkpointed Phase 1 result — the candidates this
    source proposed. Resume replays them instead of re-calling the LLM, which
    is what keeps a resumed page's `sources[]` identical to an uninterrupted
    run. `sha256` is the source content hash at extraction time: a file edited
    between runs invalidates its own checkpoint.
    """

    model_config = ConfigDict(frozen=True)

    source_id: str
    status: CheckpointStatus
    sha256: str = ""
    entity_ids: list[str] = Field(default_factory=list)
    updated_at: datetime


class HierarchyStateRecord(BaseModel):
    """Snapshot of the last hierarchy build (SPEC §6.2 — feeds incremental judge)."""

    model_config = ConfigDict(frozen=True)

    run_id: str
    page_embeddings: dict[str, list[float]] = Field(default_factory=dict)
    page_content_hashes: dict[str, str] = Field(default_factory=dict)
    cluster_membership: dict[str, str] = Field(default_factory=dict)
    cluster_summaries: dict[str, str] = Field(default_factory=dict)
    superseded_map: dict[str, str] = Field(default_factory=dict)


class StateStore(ABC):
    """Tracks sources, pages, the link graph and the run log (SPEC §3.2)."""

    @abstractmethod
    def get_source(self, source_id: str) -> SourceRecord | None: ...

    @abstractmethod
    def put_source(self, record: SourceRecord, *, run_id: str) -> None: ...

    @abstractmethod
    def remove_source(self, source_id: str, *, run_id: str) -> None: ...

    @abstractmethod
    def list_sources(self) -> list[SourceRecord]: ...

    @abstractmethod
    def get_page(self, entity_id: str) -> PageRecord | None: ...

    @abstractmethod
    def put_page(self, record: PageRecord, *, run_id: str) -> None: ...

    @abstractmethod
    def remove_page(self, entity_id: str, *, run_id: str) -> None: ...

    @abstractmethod
    def list_pages(self) -> list[PageRecord]: ...

    @abstractmethod
    def get_links(self, entity_id: str) -> list[str]: ...

    @abstractmethod
    def set_links(self, entity_id: str, targets: list[str], *, run_id: str) -> None: ...

    @abstractmethod
    def append_run(self, run_id: str, record: dict[str, Any]) -> None: ...

    @abstractmethod
    def get_checkpoints(self) -> dict[str, CompileCheckpoint]:
        """All compile checkpoints by source_id. Deliberately run_id-independent:
        a resuming compile mints a new run_id and must still see the prior run's
        progress."""

    @abstractmethod
    def put_checkpoint(self, record: CompileCheckpoint, *, run_id: str) -> None: ...

    @abstractmethod
    def clear_checkpoints(self, *, run_id: str) -> None:
        """Drop all checkpoints — only ever on a fully successful compile."""

    @abstractmethod
    def get_hierarchy_state(self) -> HierarchyStateRecord | None: ...

    @abstractmethod
    def put_hierarchy_state(self, record: HierarchyStateRecord, *, run_id: str) -> None: ...
