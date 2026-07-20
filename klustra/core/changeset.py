from pydantic import BaseModel, ConfigDict, Field


class SourceChanges(BaseModel):
    model_config = ConfigDict(frozen=True)

    added: list[str] = Field(default_factory=list)
    modified: list[str] = Field(default_factory=list)
    removed: list[str] = Field(default_factory=list)


class PageChanges(BaseModel):
    model_config = ConfigDict(frozen=True)

    added: list[str] = Field(default_factory=list)
    updated: list[str] = Field(default_factory=list)
    removed: list[str] = Field(default_factory=list)
    affected: list[str] = Field(default_factory=list)


class ChangeSet(BaseModel):
    """Output of every ingestion operation, input to incremental compile (SPEC §3.3)."""

    model_config = ConfigDict(frozen=True)

    sources: SourceChanges = Field(default_factory=SourceChanges)
    pages: PageChanges = Field(default_factory=PageChanges)
