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
