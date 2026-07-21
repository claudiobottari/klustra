from __future__ import annotations

import hashlib
import json
from typing import Any

from klustra.llm.provider import LLMProvider, LLMRequest, LLMResponse


def _minimal_from_schema(schema: dict[str, Any]) -> Any:
    """Generate minimal valid JSON from a JSON Schema."""
    schema_type = schema.get("type", "object")

    if "const" in schema:
        return schema["const"]
    if "enum" in schema:
        return schema["enum"][0]

    if schema_type == "object":
        props = schema.get("properties", {})
        required = set(schema.get("required", props.keys()))
        result: dict[str, Any] = {}
        for key, sub_schema in props.items():
            if key in required:
                result[key] = _minimal_from_schema(sub_schema)
        return result
    if schema_type == "array":
        return []
    if schema_type == "string":
        return "mock_value"
    if schema_type == "integer":
        return 0
    if schema_type == "number":
        return 0.0
    if schema_type == "boolean":
        return False
    if schema_type == "null":
        return None
    return "mock_value"


def _request_key(request: LLMRequest) -> str:
    content = "".join(m.content for m in request.messages)
    return hashlib.sha256(content.encode()).hexdigest()[:16]


class MockProvider(LLMProvider):
    """Deterministic provider for tests — no network, schema-aware fallback."""

    name = "mock"

    def __init__(self, canned: dict[str, str] | None = None) -> None:
        self._canned: dict[str, str] = canned or {}

    def add_response(self, key: str, response: str) -> None:
        self._canned[key] = response

    def call(self, request: LLMRequest) -> LLMResponse:
        key = _request_key(request)
        if key in self._canned:
            content = self._canned[key]
        elif request.response_schema is not None:
            content = json.dumps(_minimal_from_schema(request.response_schema))
        else:
            content = json.dumps({"result": "mock"})

        msg_chars = sum(len(m.content) for m in request.messages)
        tokens_in = max(1, msg_chars // 4)
        tokens_out = max(1, len(content) // 4)

        parsed = None
        if request.response_schema is not None:
            parsed = json.loads(content)

        return LLMResponse(
            content=content,
            parsed=parsed,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            model=request.model,
        )
