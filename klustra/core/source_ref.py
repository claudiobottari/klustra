from pydantic import BaseModel, ConfigDict, field_validator


class SourceRef(BaseModel):
    """Provenance entry (SPEC §3.1 sources[]) and Translator.translate() input handle (§4.1)."""

    model_config = ConfigDict(frozen=True)

    source_id: str
    source_path: str
    locator: str = ""
    translator: str = ""

    @field_validator("source_id", "source_path")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value
