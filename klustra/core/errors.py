class KlustraError(Exception):
    """Base class for all domain exceptions raised by klustra."""


class ConfigError(KlustraError):
    """klustra.toml is missing required structure or fails validation."""


class ConformanceError(KlustraError):
    """OKF conformance failure (klustra validate, SPEC §5.1) — never lint-level."""


class StateStoreError(KlustraError):
    """Base class for StateStore failures."""


class SourceNotFoundError(StateStoreError):
    """No source record exists for the given source_id."""


class PageNotFoundError(StateStoreError):
    """No page record exists for the given entity_id."""


class TranslatorNotFoundError(KlustraError):
    """No translator registered for the given file extension or URI scheme."""


class ConnectorNotFoundError(KlustraError):
    """No connector registered for the given source type."""


class ExporterNotFoundError(KlustraError):
    """No exporter registered for the given name."""


class LLMError(KlustraError):
    """Base class for LLM-layer failures."""


class LLMCallError(LLMError):
    """Network or API call failed after all retries."""


class LLMEmptyCompletionError(LLMCallError):
    """Model returned an empty or whitespace-only completion — treated as transient."""


class LLMValidationError(LLMError):
    """LLM response did not conform to the expected JSON schema."""


class LLMKeyMissingError(LLMError):
    """Required API key environment variable is not set."""
