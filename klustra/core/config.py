import os
import tomllib
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from klustra.core.errors import ConfigError


class LLMRoleConfig(BaseModel):
    """One [llm.<role>] section (SPEC §8)."""

    model_config = ConfigDict(frozen=True)

    provider: str
    model: str
    max_tokens: int | None = None


class LLMConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    extraction: LLMRoleConfig | None = None
    librarian: LLMRoleConfig | None = None
    hierarchy: LLMRoleConfig | None = None
    judge: LLMRoleConfig | None = None
    embeddings: LLMRoleConfig | None = None


class KlustraConfig(BaseModel):
    """Parsed klustra.toml (SPEC §12). Secrets stay in env — see resolve_api_key()."""

    model_config = ConfigDict(frozen=True)

    llm: LLMConfig = Field(default_factory=LLMConfig)


def load_config(path: Path | str = Path("klustra.toml")) -> KlustraConfig:
    """Load klustra.toml. Missing file yields an all-default config."""
    path = Path(path)
    if not path.exists():
        return KlustraConfig()

    try:
        with path.open("rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path}: invalid TOML: {exc}") from exc

    try:
        return KlustraConfig.model_validate(data)
    except ValidationError as exc:
        raise ConfigError(f"{path}: invalid config: {exc}") from exc


def resolve_api_key(provider: str) -> str | None:
    """Secrets live only in env (SPEC §12): "openrouter" -> OPENROUTER_API_KEY."""
    return os.environ.get(f"{provider.upper()}_API_KEY")
