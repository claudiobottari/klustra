import os
import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from klustra.core.errors import ConfigError


class LLMRoleConfig(BaseModel):
    """One [llm.<role>] section (SPEC §8)."""

    model_config = ConfigDict(frozen=True)

    provider: str
    model: str
    max_tokens: int | None = None
    base_url: str | None = None
    retry_attempts: int = 3


class LLMConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    extraction: LLMRoleConfig | None = None
    librarian: LLMRoleConfig | None = None
    hierarchy: LLMRoleConfig | None = None
    judge: LLMRoleConfig | None = None
    embeddings: LLMRoleConfig | None = None


class LintConfig(BaseModel):
    """Lint quality gate config (SPEC §5.1)."""

    model_config = ConfigDict(frozen=True)

    promote_to_error: list[str] = Field(default_factory=list)


class HierarchySettings(BaseModel):
    """Hierarchy build knobs (SPEC §6)."""

    model_config = ConfigDict(frozen=True)

    mode: Literal["hard", "soft"] = "hard"
    min_cluster_size: int = 4
    home_threshold: int = 5
    probability_threshold: float = 0.5
    materiality_threshold: float = Field(default=0.10, ge=0.0, le=1.0)
    drift_threshold_percent: float = Field(default=0.30, ge=0.0, le=1.0)
    stability_threshold: float = Field(default=0.6, ge=0.0, le=1.0)


class KlustraConfig(BaseModel):
    """Parsed klustra.toml (SPEC §12). Secrets stay in env — see resolve_api_key()."""

    model_config = ConfigDict(frozen=True)

    llm: LLMConfig = Field(default_factory=LLMConfig)
    lint: LintConfig = Field(default_factory=LintConfig)
    hierarchy: HierarchySettings = Field(default_factory=HierarchySettings)


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
