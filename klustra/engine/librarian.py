from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from typing import Any

from klustra.core.errors import LLMValidationError
from klustra.core.page import Page
from klustra.core.source_ref import SourceRef
from klustra.core.state_store import PageRecord, StateStore
from klustra.engine.models import (
    LIBRARIAN_SCHEMA,
    LibrarianOutput,
    LibrarianResult,
    SourceContribution,
)
from klustra.linking import resolve_links
from klustra.llm import (
    AccountingSink,
    LLMMessage,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    TokenRecord,
)

_CITATION_RE = re.compile(r"\^\[.+?\]")


def merge_and_generate(
    entity_id: str,
    contributions: list[SourceContribution],
    existing_index: list[str],
    domain: str,
    provider: LLMProvider,
    model: str,
    sink: AccountingSink,
    max_tokens: int | None = None,
    run_id: str = "",
) -> LibrarianResult:
    """Phase 2 Librarian: synthesize a Page from multi-source contributions (SPEC §5)."""
    request = _build_request(entity_id, contributions, existing_index, model, max_tokens)
    response = provider.call(request)

    sink.record(
        TokenRecord(
            role="librarian",
            model=model,
            tokens_in=response.tokens_in,
            tokens_out=response.tokens_out,
        )
    )

    output = _parse_output(response)

    if not _has_citations(output.body_md):
        retry_request = _build_retry_request(request, response)
        retry_response = provider.call(retry_request)
        sink.record(
            TokenRecord(
                role="librarian",
                model=model,
                tokens_in=retry_response.tokens_in,
                tokens_out=retry_response.tokens_out,
            )
        )
        output = _parse_output(retry_response)
        if not _has_citations(output.body_md):
            raise LLMValidationError(
                f"Librarian output for {entity_id} has no citations after retry"
            )

    valid_ids = set(existing_index)
    resolve_result = resolve_links(output.body_md, valid_ids)
    link_targets = [t.entity_id for t in resolve_result.resolved if t.entity_id]

    now = datetime.now(UTC)
    sources = [SourceRef(source_id=c.source_id, source_path=c.source_path) for c in contributions]

    page = Page(
        type="concept",
        level=0,
        entity_id=entity_id,
        title=output.title,
        description=output.description,
        aliases=output.aliases,
        domain=domain,
        tags=output.tags,
        confidence=output.confidence,
        sources=sources,
        created_at=now,
        updated_at=now,
    )

    return LibrarianResult(
        page=page,
        body_md=output.body_md,
        link_targets=link_targets,
    )


def persist_librarian_result(
    result: LibrarianResult,
    store: StateStore,
    run_id: str,
) -> None:
    """Write a LibrarianResult to StateStore atomically."""
    content_hash = hashlib.sha256(result.body_md.encode()).hexdigest()[:16]
    source_ids = [s.source_id for s in result.page.sources]

    record = PageRecord(
        entity_id=result.page.entity_id,
        source_ids=source_ids,
        level=result.page.level,
        content_hash=content_hash,
    )
    store.put_page(record, run_id=run_id)
    store.set_links(result.page.entity_id, result.link_targets, run_id=run_id)


def _build_request(
    entity_id: str,
    contributions: list[SourceContribution],
    existing_index: list[str],
    model: str,
    max_tokens: int | None,
) -> LLMRequest:
    system_content = (
        "You are a Librarian. Synthesize a wiki page from multiple source contributions.\n\n"
        "RULES:\n"
        "1. Every factual claim MUST have a citation: ^[source_id:locator]\n"
        "2. If sources conflict, the most recent claim wins. "
        "Put the discarded claim in a '## Storia e revisioni' section "
        "with its ^[source_id:locator] reference. NEVER silently drop claims.\n"
        "3. Use ONLY wikilinks from the provided entity index: [[entity_id]]. "
        "NEVER invent link targets.\n"
        "4. Write a coherent synthesis, not a list of per-source summaries.\n"
        "5. A page without citations will be REJECTED."
    )

    parts: list[str] = [f"## Entity: {entity_id}\n"]

    if existing_index:
        parts.append("## Valid wikilink targets")
        parts.append(", ".join(existing_index))
        parts.append("")

    for contrib in contributions:
        parts.append(f"## Source: {contrib.source_id} ({contrib.source_path})")
        for unit in contrib.units:
            parts.append(f"### [{unit.kind}] {unit.locator}")
            parts.append(unit.content_md)
            parts.append("")

    user_content = "\n".join(parts)

    return LLMRequest(
        messages=[
            LLMMessage(role="system", content=system_content),
            LLMMessage(role="user", content=user_content),
        ],
        model=model,
        max_tokens=max_tokens,
        response_schema=LIBRARIAN_SCHEMA,
    )


def _build_retry_request(original: LLMRequest, response: LLMResponse) -> LLMRequest:
    """Append citation-enforcement feedback for retry."""
    messages = list(original.messages) + [
        LLMMessage(role="assistant", content=response.content),
        LLMMessage(
            role="user",
            content=(
                "REJECTED: The page body has no citations. "
                "Every factual claim MUST include ^[source_id:locator]. "
                "Regenerate the page with proper citations."
            ),
        ),
    ]
    return LLMRequest(
        messages=messages,
        model=original.model,
        max_tokens=original.max_tokens,
        response_schema=original.response_schema,
        temperature=original.temperature,
    )


def _parse_output(response: LLMResponse) -> LibrarianOutput:
    parsed: dict[str, Any] = response.parsed or {}
    return LibrarianOutput.model_validate(parsed)


def _has_citations(body_md: str) -> bool:
    return bool(_CITATION_RE.search(body_md))
