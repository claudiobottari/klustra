"""SourceConnector registry — parallel pattern to TranslatorRegistry (SPEC §4.4)."""

from abc import ABC, abstractmethod
from pathlib import Path

from klustra.core.changeset import ChangeSet
from klustra.core.errors import ConnectorNotFoundError
from klustra.core.state_store import StateStore
from klustra.ingestion.domain_registry import LocalFolderSourceConfig, SourceConfig
from klustra.ingestion.source_manager import sync_folder
from klustra.ingestion.translator_registry import TranslatorRegistry


class SourceConnector(ABC):
    """Strategy contract for source connectors (SPEC §4.4).

    Adding a new connector (e.g. SharePoint) = one new subclass + a new ``type`` value in TOML.
    Zero changes to DomainRegistry, engine/, or hierarchy/.
    """

    type: str

    @abstractmethod
    def sync(self, source: SourceConfig, state: StateStore) -> ChangeSet: ...


class LocalFolderConnector(SourceConnector):
    """v0.1 connector: wraps ``sync_folder`` for ``type="local_folder"`` sources (SPEC §4.4)."""

    type = "local_folder"

    def __init__(self, registry: TranslatorRegistry, *, run_id: str | None = None) -> None:
        self._registry = registry
        self._run_id = run_id

    def sync(self, source: SourceConfig, state: StateStore) -> ChangeSet:
        if not isinstance(source, LocalFolderSourceConfig):
            raise TypeError(
                f"LocalFolderConnector expects LocalFolderSourceConfig, got {type(source)}"
            )
        return sync_folder(
            Path(source.path),
            state,
            self._registry,
            run_id=self._run_id,
            recursive=source.recursive,
            glob=source.glob or None,
        )


class ConnectorRegistry:
    """Maps source type strings to SourceConnector instances (SPEC §4.4)."""

    def __init__(self) -> None:
        self._connectors: dict[str, SourceConnector] = {}

    def register(self, connector: SourceConnector) -> None:
        self._connectors[connector.type] = connector

    def get(self, type_: str) -> SourceConnector:
        if type_ not in self._connectors:
            raise ConnectorNotFoundError(f"No connector for type {type_!r}")
        return self._connectors[type_]
