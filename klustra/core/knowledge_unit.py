from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator

UnitKind = Literal["narrative", "table", "record_batch", "image_text"]


class KnowledgeUnit(BaseModel):
    """One translator output unit (SPEC §4.1). unit_id is deterministic: {source_id}#{seq}."""

    model_config = ConfigDict(frozen=True)

    unit_id: str
    kind: UnitKind
    content_md: str
    records: list[dict[str, Any]] | None = None
    locator: str
    inherited_context: dict[str, Any] = {}

    @field_validator("unit_id", "locator")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value
