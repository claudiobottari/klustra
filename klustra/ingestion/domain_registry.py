"""Domain Registry — reads .klustra/domains/<label>.toml files (SPEC §4.4)."""

import tomllib
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from klustra.core.errors import ConfigError


class LocalFolderSourceConfig(BaseModel):
    """Source config for type="local_folder" (the only connector in v0.1)."""

    model_config = ConfigDict(frozen=True)

    type: Literal["local_folder"] = "local_folder"
    path: str
    recursive: bool = True
    glob: list[str] = Field(default_factory=list)


# Discriminated union — add new source types here; DomainConfig and DomainRegistry stay untouched.
SourceConfig = Annotated[LocalFolderSourceConfig, Field(discriminator="type")]


class DomainConfig(BaseModel):
    """Parsed domain TOML (SPEC §4.4): label, title, description, sources list."""

    model_config = ConfigDict(frozen=True)

    label: str
    title: str
    description: str
    sources: list[SourceConfig] = Field(default_factory=list)


def load_domain(path: Path | str) -> DomainConfig:
    """Parse a single domain TOML file. Raises ConfigError on missing/invalid file."""
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"{path}: domain config file not found")
    try:
        with path.open("rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path}: invalid TOML: {exc}") from exc
    try:
        return DomainConfig.model_validate(data)
    except ValidationError as exc:
        raise ConfigError(f"{path}: invalid domain config: {exc}") from exc


def list_domains(klustra_dir: Path | str = Path(".klustra")) -> list[DomainConfig]:
    """Load all *.toml files from <klustra_dir>/domains/. Skips files that fail validation."""
    domains_dir = Path(klustra_dir) / "domains"
    if not domains_dir.is_dir():
        return []
    return [load_domain(p) for p in sorted(domains_dir.glob("*.toml"))]


def get_domain(label: str, klustra_dir: Path | str = Path(".klustra")) -> DomainConfig | None:
    """Return the DomainConfig for *label*, or None if not found."""
    domains_dir = Path(klustra_dir) / "domains"
    candidate = domains_dir / f"{label}.toml"
    if not candidate.exists():
        return None
    return load_domain(candidate)
