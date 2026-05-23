"""
bot/formatter/formatter.py — Answer Formatting and Explanation Generation.

format_answer(result_df, query, plan, sql)     → ChatResponse
summarize_result(df, plan)                     → str
generate_explanation(plan, sql, summary, llm)  → str
estimate_query_complexity(plan)                → str
"""
from __future__ import annotations

import math
from typing import Optional

import pandas as pd
from loguru import logger

from bot.api.models import ChatResponse, IntentType, QueryPlan


# ══════════════════════════════════════════════════════════════════════════════
# Explanation prompt
# ══════════════════════════════════════════════════════════════════════════════

_EXPLAIN_SYSTEM = "You are a data analyst explaining query results to a business user. Be concise, avoid SQL jargon."

_EXPLAIN_PROMPT = """QUERY: {user_query}
TABLES USED: {tables_used}
SQL EXECUTED: {sql}
RESULT SUMMARY: {result_summary}
METRICS COMPUTED: {metrics}

Write a concise explanation (2-4 sentences) that:
- States what tables were joined and why
- Mentions any formulas used (e.g., revenue = quantity × price)
- Describes any time filters applied
- Interprets the result in business terms

Be concise. Do not repeat the SQL."""


# ══════════════════════════════════════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════════════════════════════════════


def format_answer(
    result_df: pd.DataFrame,
    query: str,
    plan: QueryPlan,
    sql: str,
    llm_client=None,  # Optional — if None, explanation is generated without LLM
    was_repaired: bool = False,
) -> ChatResponse:
    """Orchestrate formatting: summarize → explain → build ChatResponse.

    Args:
        result_df:    DataFrame returned by DuckDB.
        query:        Original user question.
        plan:         QueryPlan used.
        sql:          SQL that was executed.
        llm_client:   Optional LLMClient for explanation generation.
        was_repaired: Whether the SQL was repaired before success.

    Returns:
        Fully populated ChatResponse.
    """
    summary = summarize_result(result_df, plan)
    complexity = estimate_query_complexity(plan)

    if llm_client is not None:
        try:
            explanation = generate_explanation(plan, sql, summary, query, llm_client)
        except Exception as e:
            logger.warning(f"Explanation generation failed: {e}")
            explanation = _fallback_explanation(plan, summary)
    else:
        explanation = _fallback_explanation(plan, summary)

    # Build result preview (up to 50 rows, handle NaN serialization)
    preview_df = result_df.head(50).copy()
    # Replace NaN/NaT/inf with None for JSON serialization
    preview_df = preview_df.where(pd.notnull(preview_df), other=None)
    # Convert to dict, replacing non-serializable types
    try:
        result_preview = preview_df.to_dict(orient="records")
        # Clean non-serializable values
        result_preview = [
            {k: _safe_value(v) for k, v in row.items()}
            for row in result_preview
        ]
    except Exception:
        result_preview = []

    return ChatResponse(
        answer=summary,
        sql=sql,
        tables_used=plan.tables_needed,
        explanation=explanation,
        result_preview=result_preview,
        query_complexity=complexity,
        was_repaired=was_repaired,
    )


def summarize_result(df: pd.DataFrame, plan: QueryPlan) -> str:
    """Generate a 1-3 sentence natural language summary of the result.

    Handles:
      - Empty results
      - Single-row scalar results
      - Multi-row results
      - Revenue / metric summaries
    """
    if df is None or len(df) == 0:
        return "No matching data was found for your query."

    row_count = len(df)
    table_names = ", ".join(plan.tables_needed)

    # Single number result
    if row_count == 1 and len(df.columns) == 1:
        val = df.iloc[0, 0]
        col = df.columns[0]
        formatted = _format_value(val)
        return f"The result for '{col}' is **{formatted}**."

    # Top-N result
    if plan.intent == IntentType.TOP_N and row_count > 0:
        top_col = df.columns[0]
        top_val = df.iloc[0, 0]
        metric_cols = [c for c in df.columns if c != top_col]
        summary = f"Found **{row_count} result(s)**. "
        if metric_cols:
            top_metric = df.iloc[0][metric_cols[0]]
            summary += f"Top: **{top_val}** with {metric_cols[0]} = {_format_value(top_metric)}."
        return summary

    # Comparison / delta result
    if plan.intent in (IntentType.COMPARISON, IntentType.ANOMALY_DETECTION):
        delta_cols = [c for c in df.columns if "delta" in c.lower()]
        if delta_cols and row_count > 0:
            total_drops = row_count
            return (
                f"Found **{total_drops}** item(s) with a significant change. "
                f"Results are sorted by largest negative delta first."
            )

    # Aggregation summary
    if plan.intent == IntentType.AGGREGATION and len(plan.metrics) > 0:
        metric_name = plan.metrics[0].name
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        if numeric_cols:
            total = df[numeric_cols[0]].sum()
            return (
                f"Aggregated **{row_count}** group(s) across {table_names}. "
                f"Total {metric_name}: **{_format_value(total)}**."
            )

    # Trend
    if plan.intent == IntentType.TREND:
        return (
            f"Trend data with **{row_count}** time periods found across {table_names}."
        )

    # Generic multi-row
    return f"Found **{row_count}** result(s) from {table_names}."


def generate_explanation(
    plan: QueryPlan,
    sql: str,
    result_summary: str,
    user_query: str,
    llm_client,
) -> str:
    """Generate a business-friendly explanation using the LLM.

    Falls back to _fallback_explanation if LLM call fails.
    """
    tables_str = ", ".join(plan.tables_needed)
    metrics_str = ", ".join(
        f"{m.name} = {m.expression}" for m in plan.metrics
    ) if plan.metrics else "none"

    prompt = _EXPLAIN_PROMPT.format(
        user_query=user_query,
        tables_used=tables_str,
        sql=sql[:500],  # truncate for token limits
        result_summary=result_summary,
        metrics=metrics_str,
    )

    return llm_client.complete(prompt, system=_EXPLAIN_SYSTEM)


def estimate_query_complexity(plan: QueryPlan) -> str:
    """Classify query complexity based on plan characteristics.

    Returns a badge string like:
      'Simple lookup'
      '2-table join'
      '3-table join · Derived metric · Time comparison'
    """
    parts: list[str] = []

    n_tables = len(plan.tables_needed)
    if n_tables == 1:
        if not plan.metrics and not plan.group_by:
            parts.append("Simple lookup")
        elif plan.group_by:
            parts.append("1-table aggregate")
        else:
            parts.append("Derived metric")
    elif n_tables == 2:
        parts.append("2-table join")
    elif n_tables == 3:
        parts.append("3-table join")
    elif n_tables > 3:
        parts.append(f"{n_tables}-table join")

    if plan.metrics:
        metric_names = [m.name for m in plan.metrics]
        parts.append(f"Derived metric ({', '.join(metric_names)})")

    if plan.intent in (IntentType.COMPARISON, IntentType.ANOMALY_DETECTION):
        parts.append("Time comparison")

    if plan.intent == IntentType.TREND:
        parts.append("Trend analysis")

    if plan.intent == IntentType.TOP_N:
        limit = plan.limit or 10
        parts.append(f"Top-{limit} ranking")

    if not parts:
        parts.append("Complex analytical query")

    return " · ".join(parts)


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════


def _fallback_explanation(plan: QueryPlan, summary: str) -> str:
    """Generate a rule-based explanation without an LLM."""
    tables = ", ".join(f"'{t}'" for t in plan.tables_needed)
    joins_desc = ""
    if plan.join_paths:
        joins = [f"{jp.left_table}.{jp.left_column} → {jp.right_table}.{jp.right_column}" for jp in plan.join_paths]
        joins_desc = f" Joined via: {'; '.join(joins)}."

    metrics_desc = ""
    if plan.metrics:
        metrics = [f"{m.name} = {m.expression}" for m in plan.metrics]
        metrics_desc = f" Computed: {'; '.join(metrics)}."

    filters_desc = ""
    if plan.filters:
        filters = [f"{f.column} {f.operator} {f.value}" for f in plan.filters]
        filters_desc = f" Filters applied: {'; '.join(filters)}."

    return (
        f"This query used data from {tables}.{joins_desc}{metrics_desc}{filters_desc} "
        f"{summary}"
    )


def _format_value(val) -> str:
    """Format a scalar value for display."""
    if val is None:
        return "N/A"
    if isinstance(val, float):
        if math.isnan(val) or math.isinf(val):
            return "N/A"
        if val >= 1_000_000:
            return f"{val / 1_000_000:.2f}M"
        if val >= 1_000:
            return f"{val:,.2f}"
        return f"{val:.4f}".rstrip("0").rstrip(".")
    if isinstance(val, int):
        return f"{val:,}"
    return str(val)


def _safe_value(val) -> object:
    """Convert a value to JSON-serializable form."""
    if val is None:
        return None
    if isinstance(val, float):
        if math.isnan(val) or math.isinf(val):
            return None
        return val
    # Pandas Timestamp
    try:
        if hasattr(val, "isoformat"):
            return val.isoformat()
    except Exception:
        pass
    return val
