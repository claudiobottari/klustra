from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

SourceStatus = Literal["active", "removed"]


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
