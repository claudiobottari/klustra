from pathlib import Path

from klustra.core.errors import TranslatorNotFoundError
from klustra.ingestion.translator import Translator


class TranslatorRegistry:
    """Maps file extensions and URI schemes to Translator instances (SPEC §4.1).

    Last registration wins for a given extension/scheme.
    """

    def __init__(self) -> None:
        self._by_extension: dict[str, Translator] = {}
        self._by_scheme: dict[str, Translator] = {}

    def register(self, translator: Translator) -> None:
        for ext in translator.extensions:
            self._by_extension[ext.lower()] = translator
        for scheme in translator.schemes:
            self._by_scheme[scheme.lower()] = translator

    def get_for_path(self, path: Path | str) -> Translator:
        """Dispatch by file suffix. Raises TranslatorNotFoundError if unregistered."""
        ext = Path(path).suffix.lower()
        if ext not in self._by_extension:
            raise TranslatorNotFoundError(f"No translator for extension {ext!r}")
        return self._by_extension[ext]

    def get_for_scheme(self, scheme: str) -> Translator:
        """Dispatch by URI scheme. Raises TranslatorNotFoundError if unregistered."""
        key = scheme.lower()
        if key not in self._by_scheme:
            raise TranslatorNotFoundError(f"No translator for scheme {key!r}")
        return self._by_scheme[key]

    def extensions(self) -> frozenset[str]:
        return frozenset(self._by_extension)

    def schemes(self) -> frozenset[str]:
        return frozenset(self._by_scheme)

    def can_handle(self, path: Path | str) -> bool:
        """True if a translator is registered for this file's extension."""
        return Path(path).suffix.lower() in self._by_extension
