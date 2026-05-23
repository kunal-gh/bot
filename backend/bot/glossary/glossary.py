"""
bot/glossary/glossary.py — Business Glossary Layer.

Maps business terms to SQL expressions deterministically.
Includes time phrase resolution for DuckDB date filters.
"""
from __future__ import annotations

import re
from typing import Optional


# ══════════════════════════════════════════════════════════════════════════════
# Core Glossary: business_term → SQL expression
# ══════════════════════════════════════════════════════════════════════════════

GLOSSARY: dict[str, str] = {
    # Revenue / Sales metrics
    "revenue": "SUM(quantity * price)",
    "total revenue": "SUM(quantity * price)",
    "total sales": "SUM(quantity * price)",
    "sales": "SUM(quantity * price)",
    "gross revenue": "SUM(quantity * price)",

    # Order metrics
    "orders count": "COUNT(DISTINCT order_id)",
    "order count": "COUNT(DISTINCT order_id)",
    "number of orders": "COUNT(DISTINCT order_id)",
    "total orders": "COUNT(DISTINCT order_id)",

    # Average Order Value
    "aov": "SUM(quantity * price) / NULLIF(COUNT(DISTINCT order_id), 0)",
    "average order value": "SUM(quantity * price) / NULLIF(COUNT(DISTINCT order_id), 0)",

    # Profit
    "profit": "SUM(quantity * (price - cost))",
    "total profit": "SUM(quantity * (price - cost))",
    "gross profit": "SUM(quantity * (price - cost))",

    # Units
    "units sold": "SUM(quantity)",
    "total units": "SUM(quantity)",
    "quantity sold": "SUM(quantity)",

    # Revenue drop — comparison
    "revenue drop": "current_revenue - previous_revenue < 0",
    "sales drop": "current_revenue - previous_revenue < 0",

    # Rankings
    "top products": "ORDER BY SUM(quantity * price) DESC",
    "best sellers": "ORDER BY SUM(quantity) DESC",
}

# Aliases: alternate spellings that map to the canonical term
_ALIASES: dict[str, str] = {
    "rev": "revenue",
    "gmv": "total sales",
    "avg order value": "aov",
}


# ══════════════════════════════════════════════════════════════════════════════
# Time phrase → DuckDB date expression
# ══════════════════════════════════════════════════════════════════════════════

_TIME_PHRASES: dict[str, str] = {
    "today": "{col} >= CURRENT_DATE",
    "yesterday": "date_trunc('day', {col}) = CURRENT_DATE - INTERVAL 1 DAY",
    "last 7 days": "{col} >= CURRENT_DATE - INTERVAL 7 DAY",
    "last week": "{col} >= CURRENT_DATE - INTERVAL 7 DAY",
    "this week": "{col} >= date_trunc('week', CURRENT_DATE)",
    "last 30 days": "{col} >= CURRENT_DATE - INTERVAL 30 DAY",
    "last month": "{col} >= date_trunc('month', CURRENT_DATE - INTERVAL 1 MONTH)",
    "this month": "{col} >= date_trunc('month', CURRENT_DATE)",
    "last 90 days": "{col} >= CURRENT_DATE - INTERVAL 90 DAY",
    "last quarter": "{col} >= CURRENT_DATE - INTERVAL 90 DAY",
    "last year": "{col} >= CURRENT_DATE - INTERVAL 1 YEAR",
    "this year": "{col} >= date_trunc('year', CURRENT_DATE)",
}


# ══════════════════════════════════════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════════════════════════════════════


def resolve_business_term(term: str) -> Optional[str]:
    """Resolve a business term to its SQL expression. Case-insensitive.

    Returns None if the term is not in the glossary.
    """
    if not term:
        return None
    key = term.strip().lower()
    # Direct lookup
    if key in GLOSSARY:
        return GLOSSARY[key]
    # Alias lookup
    canonical = _ALIASES.get(key)
    if canonical and canonical in GLOSSARY:
        return GLOSSARY[canonical]
    return None


def resolve_metric_definition(metric: str) -> Optional[str]:
    """Alias for resolve_business_term — resolves metric names."""
    return resolve_business_term(metric)


def resolve_time_phrase(phrase: str, date_column: str = "created_at") -> str:
    """Resolve a time phrase to a DuckDB-compatible WHERE clause expression.

    Args:
        phrase:       Natural language time phrase (e.g., 'yesterday')
        date_column:  The column to apply the date filter to

    Returns:
        DuckDB-compatible SQL expression string, or the raw phrase if unknown.

    Examples:
        'yesterday'    → "date_trunc('day', created_at) = CURRENT_DATE - INTERVAL 1 DAY"
        'last 30 days' → "created_at >= CURRENT_DATE - INTERVAL 30 DAY"
    """
    if not phrase:
        return phrase

    key = phrase.strip().lower()
    template = _TIME_PHRASES.get(key)

    if template:
        return template.format(col=date_column)

    # Fuzzy: "last N days" pattern
    match = re.match(r"last\s+(\d+)\s+day", key)
    if match:
        n = match.group(1)
        return f"{date_column} >= CURRENT_DATE - INTERVAL {n} DAY"

    # Fuzzy: "last N weeks"
    match = re.match(r"last\s+(\d+)\s+week", key)
    if match:
        n = int(match.group(1)) * 7
        return f"{date_column} >= CURRENT_DATE - INTERVAL {n} DAY"

    # Fuzzy: "last N months"
    match = re.match(r"last\s+(\d+)\s+month", key)
    if match:
        n = match.group(1)
        return f"{date_column} >= date_trunc('month', CURRENT_DATE - INTERVAL {n} MONTH)"

    # Unknown — return a safe default that the LLM can use as context
    return f"{date_column} IS NOT NULL  /* unresolved time phrase: {phrase} */"


def list_all_terms() -> dict[str, str]:
    """Return a copy of the full glossary for LLM context building."""
    return dict(GLOSSARY)


def build_glossary_context() -> str:
    """Build a compact string representation of the glossary for LLM prompts."""
    lines = ["BUSINESS GLOSSARY (use these exact SQL expressions):"]
    for term, expr in GLOSSARY.items():
        lines.append(f"  {term!r} → {expr}")
    lines.append("")
    lines.append("TIME PHRASES (use with the identified date column):")
    for phrase, template in _TIME_PHRASES.items():
        lines.append(f"  {phrase!r} → {template}")
    return "\n".join(lines)
