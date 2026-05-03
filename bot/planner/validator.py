"""
bot/planner/validator.py — Query Plan JSON schema validation.

validate_query_plan(plan_dict) → QueryPlan
"""
from __future__ import annotations

from pydantic import ValidationError

from bot.api.models import QueryPlan


class PlanningError(Exception):
    """Raised when LLM output cannot be parsed or validated into a QueryPlan."""


def validate_query_plan(plan_dict: dict) -> QueryPlan:
    """Validate a raw dict against the QueryPlan Pydantic model.

    Args:
        plan_dict: Dictionary parsed from LLM JSON output.

    Returns:
        Validated QueryPlan instance.

    Raises:
        PlanningError: If the dict fails Pydantic validation or has schema errors.
    """
    if not isinstance(plan_dict, dict):
        raise PlanningError(f"Expected a JSON object, got {type(plan_dict).__name__}")

    # Ensure tables_needed is non-empty
    tables = plan_dict.get("tables_needed", [])
    if not tables:
        raise PlanningError("QueryPlan.tables_needed must contain at least one table name")

    # Ensure output_columns is present (can be empty list)
    if "output_columns" not in plan_dict:
        plan_dict["output_columns"] = []

    try:
        return QueryPlan.model_validate(plan_dict)
    except ValidationError as exc:
        # Format Pydantic errors into a readable message
        errors = "; ".join(
            f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}"
            for e in exc.errors()
        )
        raise PlanningError(f"Invalid QueryPlan schema: {errors}") from exc
