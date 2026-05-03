"""
bot/compiler/compiler.py — SQL Compilation Layer.

Deterministically compiles a QueryPlan into executable DuckDB SQL.

compile_plan_to_sql(plan) → str
"""
from __future__ import annotations

from bot.api.models import IntentType, QueryPlan
from bot.glossary.glossary import resolve_business_term, resolve_time_phrase


# Intents that use the CTE time-comparison pattern
_CTE_INTENTS = {IntentType.COMPARISON, IntentType.TREND, IntentType.ANOMALY_DETECTION}

# Join type mapping
_LEFT_JOIN_INTENTS = {IntentType.COMPARISON, IntentType.ANOMALY_DETECTION}


# ══════════════════════════════════════════════════════════════════════════════
# Main entry point
# ══════════════════════════════════════════════════════════════════════════════


def compile_plan_to_sql(plan: QueryPlan) -> str:
    """Compile a validated QueryPlan into a DuckDB-compatible SQL string.

    Dispatch rules:
      - comparison / trend / anomaly_detection → CTE path
      - everything else → standard SELECT path
    """
    if plan.intent in _CTE_INTENTS and _has_time_filters(plan):
        return _compile_cte(plan)
    return _compile_select(plan)


# ══════════════════════════════════════════════════════════════════════════════
# Standard SELECT compilation
# ══════════════════════════════════════════════════════════════════════════════


def _compile_select(plan: QueryPlan) -> str:
    """Assemble a standard SELECT statement from clause builders."""
    parts: list[str] = []

    select_clause = build_select_clause(plan)
    from_clause = build_from_clause(plan)
    join_clause = build_join_clause(plan)
    where_clause = build_where_clause(plan)
    group_by_clause = build_group_by_clause(plan)
    order_by_clause = build_order_by_clause(plan)

    parts.append(f"SELECT {select_clause}")
    parts.append(f"FROM {from_clause}")
    if join_clause:
        parts.append(join_clause)
    if where_clause:
        parts.append(f"WHERE {where_clause}")
    if group_by_clause:
        parts.append(f"GROUP BY {group_by_clause}")
    if order_by_clause:
        parts.append(order_by_clause)

    return "\n".join(parts)


# ══════════════════════════════════════════════════════════════════════════════
# Clause builders
# ══════════════════════════════════════════════════════════════════════════════


def build_select_clause(plan: QueryPlan) -> str:
    """Build SELECT … with aliases. Expands metric expressions from glossary."""
    parts: list[str] = []

    # Add explicit metrics first
    for metric in plan.metrics:
        # Try to resolve from glossary; use metric.expression as fallback
        expr = resolve_business_term(metric.name) or metric.expression
        safe_alias = metric.name.replace(" ", "_").replace("(", "").replace(")", "")
        parts.append(f"{expr} AS {safe_alias}")

    # Add output columns that are not already covered by metrics
    metric_names = {m.name.lower() for m in plan.metrics}
    for col in plan.output_columns:
        if col.lower() in metric_names:
            continue
        # If column contains '.' use table-qualified reference
        if "." in col:
            table, colname = col.split(".", 1)
            parts.append(f'"{table}"."{colname}"')
        else:
            parts.append(f'"{col}"')

    # Fallback: SELECT * if nothing specified
    if not parts:
        parts.append("*")

    return ",\n       ".join(parts)


def build_from_clause(plan: QueryPlan) -> str:
    """Build FROM <primary_table> AS <alias>."""
    primary = plan.primary_table or (plan.tables_needed[0] if plan.tables_needed else "unknown")
    alias = _short_alias(primary)
    return f'"{primary}" AS {alias}'


def build_join_clause(plan: QueryPlan) -> str:
    """Build JOIN clauses from plan.join_paths."""
    if not plan.join_paths:
        return ""

    join_type = "LEFT JOIN" if plan.intent in _LEFT_JOIN_INTENTS else "INNER JOIN"

    primary = plan.primary_table or (plan.tables_needed[0] if plan.tables_needed else "")
    joined_tables: set[str] = {primary}
    lines: list[str] = []

    for jp in plan.join_paths:
        # Determine which side we haven't joined yet
        if jp.right_table not in joined_tables:
            new_table = jp.right_table
            new_col = jp.right_column
            existing_table = jp.left_table
            existing_col = jp.left_column
        elif jp.left_table not in joined_tables:
            new_table = jp.left_table
            new_col = jp.left_column
            existing_table = jp.right_table
            existing_col = jp.right_column
        else:
            # Both already in FROM/JOIN — still emit the join for ON clause
            new_table = jp.right_table
            new_col = jp.right_column
            existing_table = jp.left_table
            existing_col = jp.left_column

        alias = _short_alias(new_table)
        existing_alias = _short_alias(existing_table)
        lines.append(
            f'{join_type} "{new_table}" AS {alias} '
            f'ON {existing_alias}."{existing_col}" = {alias}."{new_col}"'
        )
        joined_tables.add(new_table)

    return "\n".join(lines)


def build_where_clause(plan: QueryPlan) -> str:
    """Build WHERE clause from plan.filters. Resolves time phrases via glossary."""
    if not plan.filters:
        return ""

    conditions: list[str] = []
    date_col = plan.time_column or "created_at"

    for f in plan.filters:
        table_alias = _short_alias(f.table) if f.table else ""
        col_ref = f'{table_alias}."{f.column}"' if table_alias else f'"{f.column}"'

        op = f.operator.lower()
        val = f.value

        # Time phrase detection
        if op in ("date_equals", "date_range", "time_phrase"):
            resolved = resolve_time_phrase(val, col_ref)
            conditions.append(resolved)
            continue

        # Standard operators
        if op == "eq":
            conditions.append(f"{col_ref} = {_quote_value(val)}")
        elif op == "gt":
            conditions.append(f"{col_ref} > {_quote_value(val)}")
        elif op == "gte":
            conditions.append(f"{col_ref} >= {_quote_value(val)}")
        elif op == "lt":
            conditions.append(f"{col_ref} < {_quote_value(val)}")
        elif op == "lte":
            conditions.append(f"{col_ref} <= {_quote_value(val)}")
        elif op == "in":
            items = ", ".join(_quote_value(v.strip()) for v in val.split(","))
            conditions.append(f"{col_ref} IN ({items})")
        elif op == "like":
            conditions.append(f"{col_ref} LIKE {_quote_value(val)}")
        elif op == "not_null":
            conditions.append(f"{col_ref} IS NOT NULL")
        elif op == "is_null":
            conditions.append(f"{col_ref} IS NULL")
        else:
            # Raw expression fallback
            conditions.append(f"{col_ref} {op} {_quote_value(val)}")

    return "\n  AND ".join(conditions)


def build_group_by_clause(plan: QueryPlan) -> str:
    """Build GROUP BY clause from plan.group_by."""
    if not plan.group_by:
        return ""
    parts = []
    for col in plan.group_by:
        if "." in col:
            table, colname = col.split(".", 1)
            parts.append(f'{_short_alias(table)}."{colname}"')
        else:
            parts.append(f'"{col}"')
    return ", ".join(parts)


def build_order_by_clause(plan: QueryPlan) -> str:
    """Build ORDER BY clause. Adds LIMIT for top_n intent."""
    lines: list[str] = []

    if plan.intent == IntentType.TOP_N and plan.metrics:
        # Order by first metric DESC for ranking
        metric = plan.metrics[0]
        expr = resolve_business_term(metric.name) or metric.expression
        lines.append(f"ORDER BY {expr} DESC")
        limit = plan.limit if plan.limit is not None else 10
        lines.append(f"LIMIT {limit}")

    elif plan.intent == IntentType.TREND and plan.time_column:
        lines.append(f'ORDER BY "{plan.time_column}" ASC')

    elif plan.intent in (IntentType.AGGREGATION, IntentType.DERIVED_METRIC):
        if plan.metrics:
            metric = plan.metrics[0]
            expr = resolve_business_term(metric.name) or metric.expression
            lines.append(f"ORDER BY {expr} DESC")
        if plan.limit:
            lines.append(f"LIMIT {plan.limit}")

    elif plan.limit:
        lines.append(f"LIMIT {plan.limit}")

    return "\n".join(lines)


def build_ctes(plan: QueryPlan, periods: list[tuple[str, str]] | None = None) -> str:
    """Build CTEs for time comparison queries.

    Generates WITH period_a AS (...), period_b AS (...) SELECT ... comparison ...
    """
    if not periods:
        periods = [
            ("current_period", "yesterday"),
            ("previous_period", "day before yesterday"),
        ]

    date_col = plan.time_column or "created_at"
    primary = plan.primary_table or (plan.tables_needed[0] if plan.tables_needed else "t")
    primary_alias = _short_alias(primary)

    # Build the inner SELECT for each period
    metric_parts = []
    for metric in plan.metrics:
        expr = resolve_business_term(metric.name) or metric.expression
        alias = metric.name.replace(" ", "_")
        metric_parts.append(f"{expr} AS {alias}")

    group_cols = []
    for col in plan.group_by:
        if "." in col:
            table, colname = col.split(".", 1)
            group_cols.append(f'{_short_alias(table)}."{colname}"')
        else:
            group_cols.append(f'"{col}"')

    select_parts = group_cols + (metric_parts or ["COUNT(*) AS record_count"])

    from_part = build_from_clause(plan)
    join_part = build_join_clause(plan)

    cte_parts: list[str] = []
    for period_name, time_phrase in periods:
        time_filter = resolve_time_phrase(time_phrase, f'{primary_alias}."{date_col}"')
        inner_lines = [f"  SELECT {', '.join(select_parts)}", f"  FROM {from_part}"]
        if join_part:
            inner_lines.append(f"  {join_part}")
        inner_lines.append(f"  WHERE {time_filter}")
        if group_cols:
            inner_lines.append(f"  GROUP BY {', '.join(group_cols)}")
        cte_parts.append(f"{period_name} AS (\n" + "\n".join(inner_lines) + "\n)")

    cte_sql = "WITH " + ",\n".join(cte_parts)

    # Final SELECT joining the two periods
    cur_name, prev_name = periods[0][0], periods[1][0]
    final_cols = []
    for col in group_cols:
        col_clean = col.strip('"').replace('"', "")
        final_cols.append(f'cur."{col_clean}"')
    for metric in plan.metrics:
        alias = metric.name.replace(" ", "_")
        final_cols.append(f'cur.{alias} AS {alias}_current')
        final_cols.append(f'prev.{alias} AS {alias}_previous')
        final_cols.append(f'cur.{alias} - COALESCE(prev.{alias}, 0) AS {alias}_delta')

    if not final_cols:
        final_cols = ["cur.*", "prev.*"]

    join_on_parts = []
    for col in group_cols:
        col_clean = col.strip('"')
        join_on_parts.append(f'cur.{col_clean} = prev.{col_clean}')

    final_sql = [f"\nSELECT {', '.join(final_cols)}"]
    final_sql.append(f"FROM {cur_name} AS cur")
    if join_on_parts:
        final_sql.append(f"LEFT JOIN {prev_name} AS prev ON {' AND '.join(join_on_parts)}")
    else:
        final_sql.append(f"CROSS JOIN {prev_name} AS prev")

    # For anomaly/revenue drop: add WHERE delta < 0
    if plan.intent in (IntentType.COMPARISON, IntentType.ANOMALY_DETECTION) and plan.metrics:
        alias = plan.metrics[0].name.replace(" ", "_")
        final_sql.append(f"WHERE cur.{alias} - COALESCE(prev.{alias}, 0) < 0")
        final_sql.append(f"ORDER BY {alias}_delta ASC")

    return cte_sql + "\n" + "\n".join(final_sql)


# ══════════════════════════════════════════════════════════════════════════════
# CTE path for time comparisons
# ══════════════════════════════════════════════════════════════════════════════


def _compile_cte(plan: QueryPlan) -> str:
    """Compile time-comparison queries using the CTE pattern."""
    # Identify time filters to determine comparison windows
    time_filters = [f for f in plan.filters if f.operator in ("date_equals", "date_range", "time_phrase")]

    if not time_filters:
        # Default to yesterday vs day before
        return build_ctes(plan)

    # Map time filter values to period names
    val = time_filters[0].value.lower()
    if "yesterday" in val:
        periods = [("yesterday", "yesterday"), ("day_before", "day before yesterday")]
    elif "last week" in val or "last 7" in val:
        periods = [("this_week", "last week"), ("previous_week", "week before last")]
    elif "last month" in val or "last 30" in val:
        periods = [("this_month", "last month"), ("previous_month", "2 months ago")]
    else:
        periods = [("current_period", val), ("previous_period", "last week")]

    return build_ctes(plan, periods)


# ══════════════════════════════════════════════════════════════════════════════
# Utilities
# ══════════════════════════════════════════════════════════════════════════════


def _short_alias(table_name: str) -> str:
    """Generate a consistent short alias for a table name.

    Examples:
        'order_line_items' → 'oli'
        'orders'           → 'ord'
        'products'         → 'pro'
        'customers'        → 'cus'
    """
    if not table_name:
        return "t"
    parts = table_name.split("_")
    if len(parts) >= 2:
        return "".join(p[0] for p in parts if p)[:4]
    return table_name[:3]


def _quote_value(val: str) -> str:
    """Quote a value for SQL — numeric values unquoted, strings single-quoted."""
    stripped = val.strip()
    # Check if numeric
    try:
        float(stripped.replace(",", ""))
        return stripped
    except ValueError:
        pass
    # Already single-quoted
    if stripped.startswith("'") and stripped.endswith("'"):
        return stripped
    return f"'{stripped}'"


def _has_time_filters(plan: QueryPlan) -> bool:
    """Return True if the plan has time-phrase filters."""
    return any(f.operator in ("date_equals", "date_range", "time_phrase") for f in plan.filters)
