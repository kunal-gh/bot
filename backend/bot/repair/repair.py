"""
bot/repair/repair.py — SQL Repair Loop.

repair_sql(...)        → corrected SQL string
retry_execution(...)   → ExecutionResult
"""
from __future__ import annotations

import re

import duckdb
from loguru import logger

from bot.api.models import ExecutionResult, QueryPlan, SchemaRegistry
from bot.executor.executor import execute_sql_with_timeout
from bot.validator.validator import ReadOnlyViolationError, validate_sql


# ══════════════════════════════════════════════════════════════════════════════
# Repair prompt template
# ══════════════════════════════════════════════════════════════════════════════

_REPAIR_SYSTEM = """You are a SQL repair assistant for DuckDB.
Fix the failed SQL query. Output ONLY the corrected SQL. No prose, no markdown, no explanation."""

_REPAIR_PROMPT = """The following DuckDB SQL query failed. Fix it.

ORIGINAL SQL:
{original_sql}

ERROR MESSAGE:
{error_message}

SCHEMA (use ONLY these tables and columns):
{schema_context}

ORIGINAL ANALYTICAL INTENT:
{original_plan_json}

RULES:
- Output ONLY the corrected SQL. No prose, no markdown fences, no explanation.
- Preserve the original analytical intent exactly.
- Do NOT introduce new tables unless they are in the SCHEMA.
- Use DuckDB-compatible syntax.
- Fix only what is broken.
- Use double-quotes for identifiers, single-quotes for string values."""


# ══════════════════════════════════════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════════════════════════════════════


def repair_sql(
    original_sql: str,
    error_message: str,
    schema_context: str,
    original_plan: QueryPlan,
    llm_client,  # LLMClient — avoid circular import by not typing
) -> str:
    """Call LLM with the repair prompt. Return corrected SQL string.

    Args:
        original_sql:   The SQL that failed.
        error_message:  The DuckDB error message.
        schema_context: Current schema context string.
        original_plan:  Original QueryPlan for intent context.
        llm_client:     LLMClient instance.

    Returns:
        Corrected SQL string (markdown fences stripped).
    """
    import json

    plan_json = json.dumps(original_plan.model_dump(), indent=2, default=str)

    prompt = _REPAIR_PROMPT.format(
        original_sql=original_sql,
        error_message=error_message,
        schema_context=schema_context,
        original_plan_json=plan_json,
    )

    logger.info("Attempting SQL repair via LLM")
    logger.debug(f"Repair context — error: {error_message}")

    try:
        raw_response = llm_client.complete(prompt, system=_REPAIR_SYSTEM)
    except Exception as e:
        raise RuntimeError(f"LLM repair call failed: {e}") from e

    # Strip markdown fences if present
    fixed_sql = _strip_sql_fences(raw_response.strip())
    logger.info(f"Repaired SQL:\n{fixed_sql}")
    return fixed_sql


def retry_execution(
    fixed_sql: str,
    registry: SchemaRegistry,
    conn: duckdb.DuckDBPyConnection,
) -> ExecutionResult:
    """Validate the repaired SQL then execute it exactly once.

    Args:
        fixed_sql:  SQL returned by the repair loop.
        registry:   SchemaRegistry for validation.
        conn:       DuckDB connection.

    Returns:
        ExecutionResult with was_repaired=True on success.
    """
    # Validate first
    try:
        validation = validate_sql(fixed_sql, registry)
    except ReadOnlyViolationError as exc:
        return ExecutionResult(
            success=False,
            error_message=f"Repaired SQL still has read-only violation: {exc}",
            was_repaired=True,
        )

    if not validation.valid:
        error_str = "; ".join(validation.errors)
        logger.warning(f"Repaired SQL failed validation: {error_str}")
        return ExecutionResult(
            success=False,
            error_message=f"Repaired SQL is still invalid: {error_str}",
            was_repaired=True,
        )

    # Execute
    result = execute_sql_with_timeout(fixed_sql, conn)
    result.was_repaired = True

    if result.success:
        logger.info(f"SQL repair succeeded — {result.row_count} rows returned")
    else:
        logger.error(f"SQL repair failed after retry: {result.error_message}")

    return result


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════


def _strip_sql_fences(text: str) -> str:
    """Remove markdown code fences from LLM SQL output."""
    text = re.sub(r"^```(?:sql|SQL)?\s*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    return text.strip()
