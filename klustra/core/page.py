import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from klustra.core.source_ref import SourceRef

PageType = Literal["concept", "entity", "record-set", "cluster", "home", "index"]
ClusterAlgo = Literal["hdbscan", "gmm"]

_ENTITY_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*(\.[a-z0-9][a-z0-9_-]*)*$")


class ClusterMeta(BaseModel):
    """SPEC §3.1 `cluster_meta:` block — only present on type: cluster|home."""

    model_config = ConfigDict(frozen=True)

    algo: ClusterAlgo
    run_id: str
    cohesion: float = Field(ge=0.0, le=1.0)


class Page(BaseModel):
    """OKF-P page frontmatter (SPEC §3.1)."""

    model_config = ConfigDict(frozen=True)

    type: PageType
    level: int = Field(ge=0)
    entity_id: str
    title: str
    description: str = ""
    aliases: list[str] = Field(default_factory=list)
    domain: str
    tags: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    sources: list[SourceRef] = Field(default_factory=list)
    children: list[str] = Field(default_factory=list)
    memberships: list[str] = Field(default_factory=list)
    cluster_meta: ClusterMeta | None = None
    superseded_by: str | None = None
    created_at: datetime
    updated_at: datetime
    schema_version: str = "1.0"

    @field_validator("entity_id")
    @classmethod
    def _entity_id_is_path_like(cls, value: str) -> str:
        if not _ENTITY_ID_RE.match(value):
            raise ValueError(
                f"entity_id {value!r} must be dot-separated lowercase segments "
                "(e.g. 'prod.cable.p-laser-320kv')"
            )
        return value

    @model_validator(mode="after")
    def _enforce_level_and_type_scoping(self) -> "Page":
        if self.level == 0:
            if self.children:
                raise ValueError("children is only valid for level >= 1 pages")
        else:
            if self.sources:
                raise ValueError("sources is only valid for level 0 pages")
            if self.memberships:
                raise ValueError("memberships is only valid for level 0 pages")

        if self.cluster_meta is not None and self.type not in ("cluster", "home"):
            raise ValueError("cluster_meta is only valid for type 'cluster' or 'home'")

        return self
