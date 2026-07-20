"""Default TranslatorRegistry with all built-in translators registered.

Adding a new translator:
  1. Create ``klustra/translators/<format>.py`` subclassing ``Translator``
  2. Import and register it here — one line, zero changes outside ``translators/``
"""

from klustra.ingestion.translator_registry import TranslatorRegistry
from klustra.translators.excel import ExcelTranslator
from klustra.translators.markdown import MarkdownTranslator
from klustra.translators.text import TextTranslator


def build_default_registry() -> TranslatorRegistry:
    """Return a TranslatorRegistry with all built-in translators registered."""
    reg = TranslatorRegistry()
    reg.register(MarkdownTranslator())
    reg.register(TextTranslator())
    reg.register(ExcelTranslator())
    return reg
