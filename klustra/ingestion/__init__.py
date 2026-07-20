"""klustra.ingestion — source manager, translator registry, domain registry, connectors."""

from klustra.ingestion.connectors import ConnectorRegistry, LocalFolderConnector, SourceConnector
from klustra.ingestion.domain_registry import (
    DomainConfig,
    LocalFolderSourceConfig,
    SourceConfig,
    get_domain,
    list_domains,
    load_domain,
)
from klustra.ingestion.source_manager import (
    ingest_file,
    ingest_folder,
    remove_source,
    sync_folder,
    update_source,
)
from klustra.ingestion.translator import TranslateContext, TranslationResult, Translator
from klustra.ingestion.translator_registry import TranslatorRegistry

__all__ = [
    "Translator",
    "TranslateContext",
    "TranslationResult",
    "TranslatorRegistry",
    "ingest_file",
    "ingest_folder",
    "update_source",
    "remove_source",
    "sync_folder",
    "SourceConfig",
    "LocalFolderSourceConfig",
    "DomainConfig",
    "load_domain",
    "list_domains",
    "get_domain",
    "SourceConnector",
    "LocalFolderConnector",
    "ConnectorRegistry",
]
