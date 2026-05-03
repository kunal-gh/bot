"""
bot/planner/planner.py — Query Planning Layer.

Converts natural language to a structured QueryPlan JSON using an LLM.

build_query_plan(query, schema_context, glossary_context, llm_client) → QueryPlan
"""
from __future__ import annotations

import json
import re

from loguru import logger

from bot.api.models import QueryPlan
from bot.planner.validator import PlanningError, validate_query_plan


# ══════════════════════════════════════════════════════════════════════════════
# LLM Client Abstraction
# ══════════════════════════════════════════════════════════════════════════════


class LLMClient:
    """Thin wrapper around the OpenAI client (or Ollama compatible endpoint)."""

    def __init__(
        self,
        api_key: str = "",
        model: str = "gpt-4o",
        base_url: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 2000,
    ) -> None:
        from openai import OpenAI

        kwargs: dict = {"api_key": api_key or "dummy"}
        if base_url:
            kwargs["base_url"] = base_url

        self._client = OpenAI(**kwargs)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def complete(self, prompt: str, system: str | None = None) -> str:
        """Send a prompt to the LLM and return the response text.

        Args:
            prompt:  User prompt
            system:  Optional system message

        Returns:
            Raw string response from the LLM.
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return response.choices[0].message.content or ""


# ══════════════════════════════════════════════════════════════════════════════
# Prompt Template
# ══════════════════════════════════════════════════════════════════════════════

_PLANNER_SYSTEM_PROMPT = """You are a SQL query planner for an advanced analytical chatbot.
Your job is to analyze a user's natural language question and produce a STRUCTURED JSON PLAN (never raw SQL).
The SQL will be compiled deterministically from your plan.

CRITICAL RULES:
1. Output ONLY valid JSON. No prose, no markdown fences, no explanation.
2. Use ONLY tables and columns that exist in the SCHEMA provided.
3. NEVER hallucinate table or column names.
4. Resolve business terms using the BUSINESS GLOSSARY provided.
5. For time references, use the date columns identified in the SCHEMA.
6. ADVANCED JOINS: If a table lacks a date column (e.g. line_items), you MUST join it to its parent table (e.g. orders) to filter by date.
7. DOMAIN HEURISTICS: For "revenue", "sales", or "orders", always prefer `orders` and `order_line_items` tables over `checkouts` or `carts`.
8. When calculating a "drop" or "increase" over time, use the `trend` or `comparison` intent.
"""

_PLANNER_PROMPT_TEMPLATE = """SCHEMA:
{schema_context}

BUSINESS GLOSSARY:
{glossary_context}

USER QUERY: {user_query}

Produce a JSON query plan with EXACTLY this structure:
{{
  "intent": "<one of: lookup|aggregation|comparison|trend|top_n|join_based|derived_metric|anomaly_detection>",
  "tables_needed": ["<table_name>", ...],
  "primary_table": "<main FROM table>",
  "join_paths": [
    {{"left_table": "<t>", "left_column": "<c>", "right_table": "<t>", "right_column": "<c>"}}
  ],
  "filters": [
    {{"table": "<t>", "column": "<c>", "operator": "<eq|gt|lt|gte|lte|date_equals|date_range|in|like>", "value": "<v>"}}
  ],
  "metrics": [
    {{"name": "<metric_name>", "expression": "<sql_expression>"}}
  ],
  "group_by": ["<table.column or column>", ...],
  "output_columns": ["<alias>", ...],
  "limit": null,
  "time_column": "<date column to use for time filters, or null>"
}}

Output ONLY the JSON object. No other text."""


# ══════════════════════════════════════════════════════════════════════════════
# Main entry point
# ══════════════════════════════════════════════════════════════════════════════


def build_query_plan(
    query: str,
    schema_context: str,
    glossary_context: str,
    llm_client: LLMClient,
) -> QueryPlan:
    """Convert a natural language query to a validated QueryPlan.

    Args:
        query:            User's natural language question
        schema_context:   String representation of the SchemaRegistry
        glossary_context: String representation of the BusinessGlossary
        llm_client:       LLMClient instance

    Returns:
        Validated QueryPlan object.

    Raises:
        PlanningError: If LLM output is invalid JSON or fails schema validation.
    """
    prompt = _PLANNER_PROMPT_TEMPLATE.format(
        schema_context=schema_context,
        glossary_context=glossary_context,
        user_query=query,
    )

    logger.info(f"Planning query: {query!r}")

    try:
        raw_response = llm_client.complete(prompt, system=_PLANNER_SYSTEM_PROMPT)
    except Exception as e:
        raise PlanningError(f"LLM API call failed: {e}") from e

    logger.debug(f"LLM plan response:\n{raw_response}")

    # Parse JSON — strip markdown fences if present
    plan_dict = _extract_json(raw_response)

    # Validate against Pydantic schema
    plan = validate_query_plan(plan_dict)

    logger.info(
        f"Plan: intent={plan.intent.value}, tables={plan.tables_needed}, "
        f"joins={len(plan.join_paths)}, metrics={len(plan.metrics)}"
    )
    return plan


def _extract_json(raw: str) -> dict:
    """Extract and parse JSON from LLM output, stripping markdown if needed."""
    text = raw.strip()

    # Strip markdown code fences
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()

    # Try direct parse
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass

    # Try to find first JSON object in the text
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group())
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

    raise PlanningError(
        f"LLM did not return valid JSON. Response was:\n{raw[:500]}"
    )
