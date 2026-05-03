"""
Unit tests — bot/compiler/compiler.py
Tests: all clause builders and compile_plan_to_sql for each IntentType
"""
import pytest

from bot.api.models import (
    FilterSpec,
    IntentType,
    JoinPath,
    MetricSpec,
    QueryPlan,
)
from bot.compiler.compiler import (
    build_from_clause,
    build_group_by_clause,
    build_join_clause,
    build_order_by_clause,
    build_select_clause,
    build_where_clause,
    compile_plan_to_sql,
)


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def make_plan(**kwargs) -> QueryPlan:
    defaults = {
        "intent": IntentType.AGGREGATION,
        "tables_needed": ["orders"],
        "primary_table": "orders",
        "join_paths": [],
        "filters": [],
        "metrics": [],
        "group_by": [],
        "output_columns": ["order_id"],
        "limit": None,
        "time_column": "created_at",
    }
    defaults.update(kwargs)
    return QueryPlan(**defaults)


# ══════════════════════════════════════════════════════════════════════════════
# build_from_clause
# ══════════════════════════════════════════════════════════════════════════════

class TestBuildFromClause:
    def test_basic_from(self):
        plan = make_plan(primary_table="orders")
        result = build_from_clause(plan)
        assert '"orders"' in result
        assert " AS " in result

    def test_alias_generated(self):
        plan = make_plan(primary_table="order_line_items")
        result = build_from_clause(plan)
        # should have some short alias
        assert " AS " in result


# ══════════════════════════════════════════════════════════════════════════════
# build_join_clause
# ══════════════════════════════════════════════════════════════════════════════

class TestBuildJoinClause:
    def test_no_joins_empty_string(self):
        plan = make_plan(join_paths=[])
        assert build_join_clause(plan) == ""

    def test_single_join(self):
        plan = make_plan(
            tables_needed=["orders", "products"],
            primary_table="orders",
            join_paths=[JoinPath(
                left_table="orders", left_column="product_id",
                right_table="products", right_column="product_id"
            )]
        )
        result = build_join_clause(plan)
        assert "JOIN" in result.upper()
        assert "products" in result
        assert "product_id" in result

    def test_multiple_joins(self):
        plan = make_plan(
            tables_needed=["orders", "order_line_items", "products"],
            primary_table="orders",
            join_paths=[
                JoinPath(left_table="orders", left_column="order_id",
                         right_table="order_line_items", right_column="order_id"),
                JoinPath(left_table="order_line_items", left_column="product_id",
                         right_table="products", right_column="product_id"),
            ]
        )
        result = build_join_clause(plan)
        assert result.count("JOIN") == 2

    def test_comparison_intent_uses_left_join(self):
        plan = make_plan(
            intent=IntentType.COMPARISON,
            tables_needed=["orders", "products"],
            primary_table="orders",
            join_paths=[JoinPath(
                left_table="orders", left_column="product_id",
                right_table="products", right_column="product_id"
            )]
        )
        result = build_join_clause(plan)
        assert "LEFT JOIN" in result


# ══════════════════════════════════════════════════════════════════════════════
# build_select_clause
# ══════════════════════════════════════════════════════════════════════════════

class TestBuildSelectClause:
    def test_plain_output_columns(self):
        plan = make_plan(output_columns=["order_id", "status"])
        result = build_select_clause(plan)
        assert "order_id" in result
        assert "status" in result

    def test_metric_expression(self):
        plan = make_plan(
            metrics=[MetricSpec(name="revenue", expression="quantity * price")],
            output_columns=[],
        )
        result = build_select_clause(plan)
        # Should resolve 'revenue' from glossary or use expression
        assert "quantity" in result or "price" in result or "revenue" in result.lower()

    def test_no_columns_returns_star(self):
        plan = make_plan(metrics=[], output_columns=[])
        result = build_select_clause(plan)
        assert result == "*"


# ══════════════════════════════════════════════════════════════════════════════
# build_where_clause
# ══════════════════════════════════════════════════════════════════════════════

class TestBuildWhereClause:
    def test_empty_filters(self):
        plan = make_plan(filters=[])
        assert build_where_clause(plan) == ""

    def test_eq_filter(self):
        plan = make_plan(
            filters=[FilterSpec(table="orders", column="status", operator="eq", value="active")]
        )
        result = build_where_clause(plan)
        assert "status" in result
        assert "active" in result

    def test_date_filter_resolved(self):
        plan = make_plan(
            time_column="created_at",
            filters=[FilterSpec(table="orders", column="created_at", operator="date_equals", value="yesterday")]
        )
        result = build_where_clause(plan)
        assert result  # should not be empty
        assert "CURRENT_DATE" in result or "current_date" in result.upper()

    def test_gt_filter(self):
        plan = make_plan(
            filters=[FilterSpec(table="orders", column="total", operator="gt", value="100")]
        )
        result = build_where_clause(plan)
        assert ">" in result
        assert "100" in result

    def test_in_filter(self):
        plan = make_plan(
            filters=[FilterSpec(table="orders", column="status", operator="in", value="active,pending")]
        )
        result = build_where_clause(plan)
        assert "IN" in result.upper()


# ══════════════════════════════════════════════════════════════════════════════
# build_group_by_clause
# ══════════════════════════════════════════════════════════════════════════════

class TestBuildGroupByClause:
    def test_empty_group_by(self):
        plan = make_plan(group_by=[])
        assert build_group_by_clause(plan) == ""

    def test_single_column(self):
        plan = make_plan(group_by=["product_name"])
        result = build_group_by_clause(plan)
        assert "product_name" in result

    def test_qualified_column(self):
        plan = make_plan(group_by=["products.product_name"])
        result = build_group_by_clause(plan)
        assert "product_name" in result


# ══════════════════════════════════════════════════════════════════════════════
# build_order_by_clause
# ══════════════════════════════════════════════════════════════════════════════

class TestBuildOrderByClause:
    def test_top_n_adds_limit(self):
        plan = make_plan(
            intent=IntentType.TOP_N,
            metrics=[MetricSpec(name="revenue", expression="quantity * price")],
            limit=5,
        )
        result = build_order_by_clause(plan)
        assert "ORDER BY" in result
        assert "LIMIT 5" in result

    def test_top_n_default_limit_10(self):
        plan = make_plan(
            intent=IntentType.TOP_N,
            metrics=[MetricSpec(name="revenue", expression="quantity * price")],
            limit=None,
        )
        result = build_order_by_clause(plan)
        assert "LIMIT 10" in result

    def test_trend_orders_by_date(self):
        plan = make_plan(intent=IntentType.TREND, time_column="created_at")
        result = build_order_by_clause(plan)
        assert "ORDER BY" in result
        assert "created_at" in result

    def test_no_special_intent_no_order(self):
        plan = make_plan(intent=IntentType.LOOKUP, metrics=[], limit=None)
        result = build_order_by_clause(plan)
        assert result == ""


# ══════════════════════════════════════════════════════════════════════════════
# compile_plan_to_sql — end-to-end per IntentType
# ══════════════════════════════════════════════════════════════════════════════

class TestCompilePlanToSQL:
    def test_lookup_produces_select(self):
        plan = make_plan(intent=IntentType.LOOKUP, output_columns=["order_id", "status"])
        sql = compile_plan_to_sql(plan)
        assert sql.upper().startswith("SELECT")
        assert "orders" in sql

    def test_aggregation_has_group_by(self):
        plan = make_plan(
            intent=IntentType.AGGREGATION,
            metrics=[MetricSpec(name="revenue", expression="quantity * price")],
            group_by=["product_name"],
        )
        sql = compile_plan_to_sql(plan)
        assert "GROUP BY" in sql.upper()

    def test_top_n_has_limit(self):
        plan = make_plan(
            intent=IntentType.TOP_N,
            metrics=[MetricSpec(name="revenue", expression="quantity * price")],
            limit=5,
        )
        sql = compile_plan_to_sql(plan)
        assert "LIMIT 5" in sql

    def test_three_table_join(self):
        plan = make_plan(
            tables_needed=["orders", "order_line_items", "products"],
            primary_table="orders",
            join_paths=[
                JoinPath(left_table="orders", left_column="order_id",
                         right_table="order_line_items", right_column="order_id"),
                JoinPath(left_table="order_line_items", left_column="product_id",
                         right_table="products", right_column="product_id"),
            ]
        )
        sql = compile_plan_to_sql(plan)
        assert sql.count("JOIN") == 2

    def test_comparison_produces_cte(self):
        plan = make_plan(
            intent=IntentType.COMPARISON,
            metrics=[MetricSpec(name="revenue", expression="quantity * price")],
            filters=[FilterSpec(
                table="orders", column="created_at",
                operator="date_equals", value="yesterday"
            )],
            time_column="created_at",
        )
        sql = compile_plan_to_sql(plan)
        assert "WITH" in sql.upper()
        assert "AS (" in sql
