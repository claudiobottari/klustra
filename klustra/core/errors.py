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


class CompileIncompleteError(KlustraError):
    """Phase 1 did not finish for every tracked source, so the Librarian merge
    was refused: merging a partial contribution set would silently drop the
    provenance of sources whose extraction never ran. Re-run compile to resume."""


class LLMError(KlustraError):
    """Base class for LLM-layer failures."""


class LLMCallError(LLMError):
    """Network or API call failed after all retries."""


class LLMEmptyCompletionError(LLMCallError):
    """Model returned an empty or whitespace-only completion — treated as transient."""


class LLMRateLimitError(LLMCallError):
    """Provider signaled rate limiting or overload (HTTP 429, or an OpenRouter
    provider_error_code like 'engine_overloaded' in the error body).

    Resolves in seconds-to-minutes, not milliseconds — gets a longer backoff
    than other transient LLMCallErrors (see llm/retry.py's wait strategy).
    """


class LLMValidationError(LLMError):
    """LLM response did not conform to the expected JSON schema.

    Carries the raw model output (when available) so the corrective-retry loop
    can feed the bad response back to the model as context (CLAUDE.md rule 3:
    validation failure = retry with error feedback, then hard fail).
    """

    def __init__(self, message: str, *, raw_content: str | None = None) -> None:
        super().__init__(message)
        self.raw_content = raw_content


class LLMInputTooLargeError(LLMError):
    """Request content exceeds the configured input-token budget.

    Deliberately NOT an LLMCallError: retrying the identical oversized input is
    guaranteed to fail again. Callers must chunk (see engine/chunking.py), not
    retry — this error is the runtime bound that fires when even the finest
    split cannot fit, or when the prompt scaffolding alone blows the budget.
    """


class LLMKeyMissingError(LLMError):
    """Required API key environment variable is not set."""
