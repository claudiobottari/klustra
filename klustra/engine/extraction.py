from __future__ import annotations

import logging
from typing import Any

from klustra.core.errors import LLMInputTooLargeError
from klustra.core.knowledge_unit import KnowledgeUnit
from klustra.engine.chunking import chunk_text
from klustra.engine.models import (
    CONCEPT_CANDIDATES_SCHEMA,
    ConceptCandidate,
    ExtractionResult,
)
from klustra.llm import (
    AccountingSink,
    LLMMessage,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    PromptRegistry,
    TokenRecord,
)
from klustra.llm.tokens import count_tokens
from klustra.logging_setup import log_op

logger = logging.getLogger(__name__)

DEFAULT_MAX_INPUT_TOKENS = 24_000

_MIN_CONTENT_TOKENS = 256
"""If scaffolding leaves less than this for content, the budget is unusable."""


def extract_concepts(
    units: list[KnowledgeUnit],
    source_id: str,
    existing_index: list[str],
    provider: LLMProvider,
    model: str,
    sink: AccountingSink,
    max_tokens: int | None = None,
    retry_attempts: int | None = None,
    max_input_tokens: int = DEFAULT_MAX_INPUT_TOKENS,
    prompts: PromptRegistry | None = None,
) -> list[ExtractionResult]:
    """Phase 1 extraction: LLM structured output for concept candidates (SPEC §5).

    Oversized units are chunked (SPEC §5.2) and mapped over multiple calls; the
    partial candidates are accumulated back onto the unit's single
    ExtractionResult, so Phase 2's existing per-entity merge does the reducing.
    """
    results: list[ExtractionResult] = []

    total_units = len(units)
    for unit_idx, unit in enumerate(units, start=1):
        # Chunking re-tokenizes the accumulating chunk per block, so this step
        # alone can run tens of seconds on a very large unit — it must not be
        # the silent prelude to everything else.
        with log_op(
            "extraction",
            "chunking",
            source_id=source_id,
            unit_id=unit.unit_id,
            unit=f"{unit_idx}/{total_units}",
            chars=len(unit.content_md),
            heartbeat=True,
        ):
            chunks = _chunks_for(unit, existing_index, max_input_tokens, prompts)
        if len(chunks) > 1:
            logger.info(
                "[compile] chunking triggered: %d chunks, source_id=%s, unit_id=%s, "
                "reason=token_count>threshold(%d)",
                len(chunks),
                source_id,
                unit.unit_id,
                max_input_tokens,
            )

        candidates: list[ConceptCandidate] = []
        seen: set[str] = set()

        for chunk_idx, chunk in enumerate(chunks, start=1):
            if len(chunks) > 1:
                logger.info(
                    "[compile] extracting chunk %d/%d of unit %s",
                    chunk_idx,
                    len(chunks),
                    unit.unit_id,
                )
            request = _build_request(
                unit,
                existing_index,
                model,
                max_tokens,
                retry_attempts,
                source_id,
                chunk,
                prompts=prompts,
            )
            input_tokens = _verify_bounds(request, max_input_tokens, unit.unit_id)
            with log_op(
                "extraction",
                "llm_call",
                source_id=source_id,
                unit_id=unit.unit_id,
                chunk=f"{chunk_idx}/{len(chunks)}",
                input_tokens=input_tokens,
                model=model,
                heartbeat=True,
            ):
                response = provider.call(request)

            sink.record(
                TokenRecord(
                    role="extraction",
                    model=model,
                    tokens_in=response.tokens_in,
                    tokens_out=response.tokens_out,
                    chunks_used=len(chunks),
                )
            )

            for candidate in _parse_response(response):
                if candidate.entity_id_proposal in seen:
                    continue
                seen.add(candidate.entity_id_proposal)
                candidates.append(candidate)

        results.append(
            ExtractionResult(
                source_id=source_id,
                unit_id=unit.unit_id,
                candidates=candidates,
            )
        )

    return results


def _chunks_for(
    unit: KnowledgeUnit,
    existing_index: list[str],
    max_input_tokens: int,
    prompts: PromptRegistry | None = None,
) -> list[str]:
    """Content budget = ceiling minus the real cost of the prompt scaffolding."""
    scaffolding = _build_request(unit, existing_index, "", None, None, "", "", prompts=prompts)
    overhead = sum(count_tokens(m.content) for m in scaffolding.messages)
    budget = max_input_tokens - overhead
    if budget < _MIN_CONTENT_TOKENS:
        raise LLMInputTooLargeError(
            f"extraction prompt scaffolding alone needs {overhead} tokens of the "
            f"{max_input_tokens} budget, leaving {budget} for content "
            f"(unit {unit.unit_id}). Raise extraction.max_input_tokens or shrink "
            f"the entity index ({len(existing_index)} entries)."
        )
    return chunk_text(unit.content_md, budget)


def _verify_bounds(request: LLMRequest, max_input_tokens: int, unit_id: str) -> int:
    """Runtime bound check — the config value is not trusted on its own.
    Returns the counted input tokens so the caller can log them."""
    total = sum(count_tokens(m.content) for m in request.messages)
    if total > max_input_tokens:
        raise LLMInputTooLargeError(
            f"extraction request for unit {unit_id} is {total} tokens, over the "
            f"{max_input_tokens} budget even after chunking"
        )
    return total


def _build_request(
    unit: KnowledgeUnit,
    existing_index: list[str],
    model: str,
    max_tokens: int | None,
    retry_attempts: int | None = None,
    source_id: str = "",
    content: str | None = None,
    prompts: PromptRegistry | None = None,
    domain_instructions: str = "",
) -> LLMRequest:
    registry = prompts or PromptRegistry()

    system_content = registry.render(
        "extraction", kind="system", domain_instructions=domain_instructions
    )
    user_content = registry.render(
        "extraction",
        kind="user",
        index_str=", ".join(existing_index) if existing_index else "(empty)",
        unit=unit,
        content=unit.content_md if content is None else content,
    )
    return LLMRequest(
        messages=[
            LLMMessage(role="system", content=system_content),
            LLMMessage(role="user", content=user_content),
        ],
        model=model,
        max_tokens=max_tokens,
        response_schema=CONCEPT_CANDIDATES_SCHEMA,
        retry_attempts=retry_attempts,
        label=f"extraction:{source_id}:{unit.unit_id}",
    )


def _parse_response(response: LLMResponse) -> list[ConceptCandidate]:
    parsed: dict[str, Any] = response.parsed or {}
    raw_candidates = parsed.get("candidates", [])
    candidates: list[ConceptCandidate] = []
    for raw in raw_candidates:
        candidates.append(ConceptCandidate.model_validate(raw))
    return candidates
