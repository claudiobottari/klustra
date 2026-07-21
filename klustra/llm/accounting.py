from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, ConfigDict


class TokenRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    role: str
    model: str
    tokens_in: int
    tokens_out: int


class AccountingSink(ABC):
    """Pluggable destination for token usage records (SPEC §9)."""

    @abstractmethod
    def record(self, entry: TokenRecord) -> None: ...


class NullSink(AccountingSink):
    def record(self, entry: TokenRecord) -> None:
        pass


class ListSink(AccountingSink):
    def __init__(self) -> None:
        self.entries: list[TokenRecord] = []

    def record(self, entry: TokenRecord) -> None:
        self.entries.append(entry)

    @property
    def total_tokens_in(self) -> int:
        return sum(e.tokens_in for e in self.entries)

    @property
    def total_tokens_out(self) -> int:
        return sum(e.tokens_out for e in self.entries)
