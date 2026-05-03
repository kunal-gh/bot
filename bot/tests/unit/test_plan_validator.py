"""
Unit tests — bot/planner/validator.py
Tests: validate_query_plan
"""
import pytest
from pydantic import ValidationError

from bot.api.models import IntentType, QueryPlan
from bot.planner.validator import PlanningError, validate_query_plan


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _valid_plan_dict(**overrides) -> dict:
    """Return a minimal valid QueryPlan dict with optional overrides."""
    base = {
        "intent": "aggregation",
        "tables_needed": ["orders"],
        "primary_table": "orders",
        "join_paths": [],
        "filters": [],
        "metrics": [],
        "group_by": [],
        "output_columns": ["order_id"],
        "limit": None,
        "time_column": None,
    }
    base.update(overrides)
    return base


# ══════════════════════════════════════════════════════════════════════════════
# Valid plans
# ══════════════════════════════════════════════════════════════════════════════

class TestValidQueryPlans:
    def test_minimal_valid_plan(self):
        plan = validate_query_plan(_valid_plan_dict())
        assert isinstance(plan, QueryPlan)
        assert plan.intent == IntentType.AGGREGATION

    def test_all_intent_types_accepted(self):
        intents = ["lookup", "aggregation", "comparison", "trend", "top_n",
                   "join_based", "derived_metric", "anomaly_detection"]
        for intent in intents:
            plan = validate_query_plan(_valid_plan_dict(intent=intent))
            assert plan.intent.value == intent

    def test_join_paths_parsed(self):
        d = _valid_plan_dict(
            tables_needed=["orders", "products"],
            join_paths=[{
                "left_table": "orders",
                "left_column": "product_id",
                "right_table": "products",
                "right_column": "product_id",
            }]
        )
        plan = validate_query_plan(d)
        assert len(plan.join_paths) == 1
        assert plan.join_paths[0].left_table == "orders"

    def test_filters_parsed(self):
        d = _valid_plan_dict(
            filters=[{"table": "orders", "column": "status", "operator": "eq", "value": "active"}]
        )
        plan = validate_query_plan(d)
        assert len(plan.filters) == 1
        assert plan.filters[0].operator == "eq"

    def test_metrics_parsed(self):
        d = _valid_plan_dict(
            metrics=[{"name": "revenue", "expression": "quantity * price"}]
        )
        plan = validate_query_plan(d)
        assert len(plan.metrics) == 1
        assert plan.metrics[0].name == "revenue"

    def test_top_n_with_limit(self):
        plan = validate_query_plan(_valid_plan_dict(intent="top_n", limit=5))
        assert plan.limit == 5

    def test_output_columns_defaults_to_empty(self):
        d = _valid_plan_dict()
        del d["output_columns"]
        plan = validate_query_plan(d)
        assert isinstance(plan.output_columns, list)


# ══════════════════════════════════════════════════════════════════════════════
# Invalid plans
# ══════════════════════════════════════════════════════════════════════════════

class TestInvalidQueryPlans:
    def test_missing_intent_raises(self):
        d = _valid_plan_dict()
        del d["intent"]
        with pytest.raises(PlanningError):
            validate_query_plan(d)

    def test_invalid_intent_raises(self):
        with pytest.raises(PlanningError):
            validate_query_plan(_valid_plan_dict(intent="nonsense"))

    def test_empty_tables_needed_raises(self):
        with pytest.raises(PlanningError):
            validate_query_plan(_valid_plan_dict(tables_needed=[]))

    def test_non_dict_input_raises(self):
        with pytest.raises(PlanningError):
            validate_query_plan("this is a string")  # type: ignore

    def test_none_input_raises(self):
        with pytest.raises(PlanningError):
            validate_query_plan(None)  # type: ignore

    def test_invalid_filter_structure_raises(self):
        d = _valid_plan_dict(
            filters=[{"table": "orders"}]  # missing column, operator, value
        )
        with pytest.raises(PlanningError):
            validate_query_plan(d)

    def test_invalid_join_path_structure_raises(self):
        d = _valid_plan_dict(
            join_paths=[{"left_table": "orders"}]  # incomplete
        )
        with pytest.raises(PlanningError):
            validate_query_plan(d)
