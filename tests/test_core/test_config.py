from pathlib import Path

import pytest

from klustra.core.config import KlustraConfig, load_config, resolve_api_key
from klustra.core.errors import ConfigError


def test_load_config_missing_file_returns_defaults(tmp_path):
    cfg = load_config(tmp_path / "does-not-exist.toml")
    assert cfg == KlustraConfig()
    assert cfg.llm.extraction is None


def test_load_config_parses_llm_roles(tmp_path: Path):
    toml_text = """
[llm.extraction]
provider = "openrouter"
model = "deepseek/deepseek-v4-flash"
max_tokens = 4096

[llm.librarian]
provider = "openrouter"
model = "deepseek/deepseek-v4-pro"
"""
    config_path = tmp_path / "klustra.toml"
    config_path.write_text(toml_text)

    cfg = load_config(config_path)
    assert cfg.llm.extraction is not None
    assert cfg.llm.extraction.provider == "openrouter"
    assert cfg.llm.extraction.max_tokens == 4096
    assert cfg.llm.librarian is not None
    assert cfg.llm.librarian.max_tokens is None
    assert cfg.llm.judge is None


def test_load_config_invalid_toml_raises_config_error(tmp_path: Path):
    config_path = tmp_path / "klustra.toml"
    config_path.write_text("this is not [valid toml")

    with pytest.raises(ConfigError):
        load_config(config_path)


def test_load_config_invalid_structure_raises_config_error(tmp_path: Path):
    config_path = tmp_path / "klustra.toml"
    # missing required "model" field
    config_path.write_text('[llm.extraction]\nprovider = "openrouter"\n')

    with pytest.raises(ConfigError):
        load_config(config_path)


def test_resolve_api_key_from_env(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-123")
    assert resolve_api_key("openrouter") == "sk-test-123"


def test_resolve_api_key_missing_returns_none(monkeypatch):
    monkeypatch.delenv("SOME_PROVIDER_API_KEY", raising=False)
    assert resolve_api_key("some_provider") is None
