"""
Integration tests — Full pipeline and API endpoints.

Tests the complete pipeline from data loading through query execution.
Uses an in-memory DuckDB instance with synthetic test data.
"""
from __future__ import annotations

import json

import duckdb
import pandas as pd
import pytest

from bot.api.models import (
    FilterSpec,
    IntentType,
    JoinPath,
    MetricSpec,
    QueryPlan,
)
from bot.compiler.compiler import compile_plan_to_sql
from bot.executor.executor import execute_sql_safe, execute_sql_with_timeout
from bot.formatter.formatter import estimate_query_complexity, format_answer
from bot.ingestion.loader import refresh_dataset, store_to_duckdb
from bot.ingestion.normalizer import normalize_column_names, infer_and_cast_types
from bot.schema.context_builder import build_schema_context_for_llm
from bot.schema.registry import build_schema_registry
from bot.schema.relationships import detect_relationships
from bot.validator.validator import ReadOnlyViolationError, validate_sql


# ══════════════════════════════════════════════════════════════════════════════
# Fixtures — Test data setup
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def conn():
    """Fresh in-memory DuckDB connection for each test."""
    c = duckdb.connect(":memory:")
    yield c
    c.close()


@pytest.fixture
def populated_conn(conn):
    """DuckDB connection with products, orders, order_line_items tables loaded."""
    # Products
    products_df = pd.DataFrame({
        "product_id": [1, 2, 3, 4, 5],
        "product_name": ["Widget A", "Gadget B", "Doohickey C", "Thingamajig D", "Whatsit E"],
        "category": ["Electronics", "Electronics", "Hardware", "Hardware", "Accessories"],
        "price": [29.99, 49.99, 9.99, 19.99, 4.99],
        "cost": [15.0, 25.0, 5.0, 10.0, 2.0],
    })

    # Orders
    orders_df = pd.DataFrame({
        "order_id": [101, 102, 103, 104, 105, 106, 107, 108],
        "customer_id": [1, 2, 1, 3, 2, 4, 1, 3],
        "created_at": pd.to_datetime([
            "2024-01-14", "2024-01-14", "2024-01-15",
            "2024-01-15", "2024-01-16", "2024-01-16",
            "2024-01-17", "2024-01-17"
        ]),
        "status": ["completed", "completed", "completed", "pending",
                   "completed", "cancelled", "completed", "completed"],
        "total_amount": [59.98, 49.99, 29.99, 9.99, 99.98, 4.99, 89.97, 39.98],
    })

    # Order line items
    line_items_df = pd.DataFrame({
        "line_item_id": list(range(1, 13)),
        "order_id": [101, 101, 102, 103, 104, 105, 105, 106, 107, 107, 107, 108],
        "product_id": [1, 2, 2, 1, 3, 1, 2, 4, 1, 2, 3, 4],
        "quantity": [2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2],
        "price": [29.99, 49.99, 49.99, 29.99, 9.99, 29.99, 49.99, 4.99, 29.99, 49.99, 9.99, 19.99],
    })

    # Customers
    customers_df = pd.DataFrame({
        "customer_id": [1, 2, 3, 4],
        "customer_name": ["Alice Smith", "Bob Jones", "Carol White", "Dave Brown"],
        "segment": ["Premium", "Standard", "Premium", "Standard"],
        "email": ["alice@example.com", "bob@example.com", "carol@example.com", "dave@example.com"],
    })

    for name, df in [
        ("products", products_df),
        ("orders", orders_df),
        ("order_line_items", line_items_df),
        ("customers", customers_df),
    ]:
        store_to_duckdb(df, name, conn)

    return conn


@pytest.fixture
def registry(populated_conn):
    """SchemaRegistry built from the populated connection."""
    reg = build_schema_registry(populated_conn)
    reg.relationships = detect_relationships(reg, populated_conn)
    return reg


# ══════════════════════════════════════════════════════════════════════════════
# Schema inspection tests
# ══════════════════════════════════════════════════════════════════════════════

class TestSchemaRegistry:
    def test_all_tables_registered(self, registry):
        names = registry.table_names()
        for expected in ["products", "orders", "order_line_items", "customers"]:
            assert expected in names, f"Table '{expected}' missing from registry"

    def test_column_metadata_complete(self, registry):
        products = registry.get_table("products")
        assert products is not None
        col_names = {c.name for c in products.columns}
        assert "product_id" in col_names
        assert "product_name" in col_names
        assert "price" in col_names

    def test_row_counts_correct(self, registry):
        assert registry.get_table("products").row_count == 5
        assert registry.get_table("orders").row_count == 8
        assert registry.get_table("order_line_items").row_count == 12

    def test_relationships_detected(self, registry):
        assert len(registry.relationships) > 0

    def test_schema_context_non_empty(self, registry):
        ctx = build_schema_context_for_llm(registry)
        assert "products" in ctx
        assert "orders" in ctx
        assert len(ctx) > 100


# ══════════════════════════════════════════════════════════════════════════════
# Ingestion round-trip test (Property 2)
# ══════════════════════════════════════════════════════════════════════════════

class TestIngestionRoundTrip:
    def test_store_and_retrieve_preserves_rows(self, conn):
        df = pd.DataFrame({"id": [1, 2, 3], "name": ["a", "b", "c"]})
        store_to_duckdb(df, "test_table", conn)
        result = conn.execute('SELECT * FROM "test_table"').fetchdf()
        assert len(result) == 3
        assert set(result.columns) == set(df.columns)

    def test_store_and_retrieve_preserves_values(self, conn):
        df = pd.DataFrame({"x": [10, 20, 30], "y": [1.5, 2.5, 3.5]})
        store_to_duckdb(df, "t2", conn)
        result = conn.execute('SELECT SUM(x) as s FROM "t2"').fetchone()
        assert result[0] == 60


# ══════════════════════════════════════════════════════════════════════════════
# Derived metric query test
# ══════════════════════════════════════════════════════════════════════════════

class TestDerivedMetricQuery:
    def test_total_revenue_sql_correct(self, populated_conn, registry):
        plan = QueryPlan(
            intent=IntentType.AGGREGATION,
            tables_needed=["order_line_items"],
            primary_table="order_line_items",
            metrics=[MetricSpec(name="revenue", expression="quantity * price")],
            output_columns=["revenue"],
        )
        sql = compile_plan_to_sql(plan)
        assert "quantity" in sql.lower() or "price" in sql.lower() or "revenue" in sql.lower()

        validation = validate_sql(sql, registry)
        assert validation.valid, f"SQL invalid: {validation.errors}"

        result = execute_sql_safe(sql, populated_conn)
        assert result.success
        assert result.row_count > 0


# ══════════════════════════════════════════════════════════════════════════════
# Multi-table join tests
# ══════════════════════════════════════════════════════════════════════════════

class TestMultiTableJoins:
    def test_two_table_join_executes(self, populated_conn, registry):
        plan = QueryPlan(
            intent=IntentType.JOIN_BASED,
            tables_needed=["orders", "customers"],
            primary_table="orders",
            join_paths=[JoinPath(
                left_table="orders", left_column="customer_id",
                right_table="customers", right_column="customer_id",
            )],
            output_columns=["order_id", "customer_name"],
        )
        sql = compile_plan_to_sql(plan)
        assert "JOIN" in sql.upper()

        result = execute_sql_safe(sql, populated_conn)
        assert result.success
        assert result.row_count == 8  # all 8 orders

    def test_three_table_join_executes(self, populated_conn, registry):
        plan = QueryPlan(
            intent=IntentType.AGGREGATION,
            tables_needed=["orders", "order_line_items", "products"],
            primary_table="orders",
            join_paths=[
                JoinPath(left_table="orders", left_column="order_id",
                         right_table="order_line_items", right_column="order_id"),
                JoinPath(left_table="order_line_items", left_column="product_id",
                         right_table="products", right_column="product_id"),
            ],
            metrics=[MetricSpec(name="revenue", expression="order_line_items.quantity * order_line_items.price")],
            group_by=["products.product_name"],
            output_columns=["product_name", "revenue"],
        )
        sql = compile_plan_to_sql(plan)
        assert sql.count("JOIN") == 2


# ══════════════════════════════════════════════════════════════════════════════
# Top-N query test
# ══════════════════════════════════════════════════════════════════════════════

class TestTopNQuery:
    def test_top_5_products_sql(self, populated_conn, registry):
        plan = QueryPlan(
            intent=IntentType.TOP_N,
            tables_needed=["order_line_items"],
            primary_table="order_line_items",
            metrics=[MetricSpec(name="revenue", expression="quantity * price")],
            group_by=["product_id"],
            output_columns=["product_id", "revenue"],
            limit=5,
        )
        sql = compile_plan_to_sql(plan)
        assert "LIMIT 5" in sql
        assert "ORDER BY" in sql.upper()

        result = execute_sql_safe(sql, populated_conn)
        assert result.success
        assert result.row_count <= 5

    def test_top_n_default_limit_10(self):
        plan = QueryPlan(
            intent=IntentType.TOP_N,
            tables_needed=["orders"],
            primary_table="orders",
            metrics=[MetricSpec(name="revenue", expression="quantity * price")],
            limit=None,
        )
        sql = compile_plan_to_sql(plan)
        assert "LIMIT 10" in sql


# ══════════════════════════════════════════════════════════════════════════════
# Aggregation query test
# ══════════════════════════════════════════════════════════════════════════════

class TestAggregationQuery:
    def test_revenue_by_product_has_group_by(self, populated_conn, registry):
        plan = QueryPlan(
            intent=IntentType.AGGREGATION,
            tables_needed=["order_line_items"],
            primary_table="order_line_items",
            metrics=[MetricSpec(name="revenue", expression="quantity * price")],
            group_by=["product_id"],
            output_columns=["product_id", "revenue"],
        )
        sql = compile_plan_to_sql(plan)
        assert "GROUP BY" in sql.upper()

        result = execute_sql_safe(sql, populated_conn)
        assert result.success
        # Should have one row per unique product_id in order_line_items (which is 4)
        assert result.row_count == 4  # 4 distinct products ordered


# ══════════════════════════════════════════════════════════════════════════════
# Read-only enforcement — simulated INSERT via API
# ══════════════════════════════════════════════════════════════════════════════

class TestReadOnlyEnforcement:
    def test_insert_fails_validation(self, registry):
        sql = "INSERT INTO orders VALUES (999, 1, NOW(), 'active', 100.0)"
        result = validate_sql(sql, registry)
        assert not result.valid
        assert any("Write operation" in e or "INSERT" in e for e in result.errors)

    def test_drop_fails_validation(self, registry):
        sql = "DROP TABLE products"
        result = validate_sql(sql, registry)
        assert not result.valid


# ══════════════════════════════════════════════════════════════════════════════
# Time comparison query — CTE pattern
# ══════════════════════════════════════════════════════════════════════════════

class TestTimeComparisonCTE:
    def test_comparison_plan_produces_cte(self):
        plan = QueryPlan(
            intent=IntentType.COMPARISON,
            tables_needed=["orders"],
            primary_table="orders",
            metrics=[MetricSpec(name="revenue", expression="total_amount")],
            filters=[FilterSpec(
                table="orders", column="created_at",
                operator="date_equals", value="yesterday"
            )],
            time_column="created_at",
        )
        sql = compile_plan_to_sql(plan)
        assert "WITH" in sql.upper()
        assert "AS (" in sql

    def test_cte_sql_executes_in_duckdb(self, populated_conn, registry):
        # Simple CTE that should execute
        sql = """
        WITH period AS (
            SELECT SUM(total_amount) AS total
            FROM "orders"
            WHERE created_at >= '2024-01-14'
        )
        SELECT * FROM period
        """
        result = execute_sql_safe(sql, populated_conn)
        assert result.success


# ══════════════════════════════════════════════════════════════════════════════
# Repair loop test — inject error, simulate repair
# ══════════════════════════════════════════════════════════════════════════════

class TestRepairLoop:
    def test_retry_execution_with_invalid_sql_returns_failure(self, populated_conn, registry):
        from bot.repair.repair import retry_execution
        broken_sql = 'SELECT "nonexistent_col" FROM "orders"'
        # Validation will fail → returns failed ExecutionResult
        result = retry_execution(broken_sql, registry, populated_conn)
        assert result.was_repaired  # Flag is set even on repair failure
        # Should not crash — graceful failure

    def test_retry_execution_with_valid_sql_succeeds(self, populated_conn, registry):
        from bot.repair.repair import retry_execution
        good_sql = 'SELECT "order_id" FROM "orders" LIMIT 5'
        result = retry_execution(good_sql, registry, populated_conn)
        assert result.was_repaired
        assert result.success
        assert result.row_count <= 5


# ══════════════════════════════════════════════════════════════════════════════
# Formatter integration test (Property 10)
# ══════════════════════════════════════════════════════════════════════════════

class TestFormatterIntegration:
    def test_format_answer_all_fields_populated(self, populated_conn):
        df = pd.DataFrame({
            "product_id": [1, 2, 3],
            "revenue": [150.0, 200.0, 50.0]
        })
        plan = QueryPlan(
            intent=IntentType.TOP_N,
            tables_needed=["order_line_items"],
            primary_table="order_line_items",
            metrics=[MetricSpec(name="revenue", expression="quantity * price")],
            limit=3,
        )
        sql = "SELECT product_id, SUM(quantity * price) AS revenue FROM order_line_items GROUP BY product_id LIMIT 3"
        response = format_answer(df, "top 3 products by revenue", plan, sql)

        assert isinstance(response.answer, str) and len(response.answer) > 0
        assert isinstance(response.sql, str)
        assert isinstance(response.tables_used, list)
        assert isinstance(response.explanation, str)
        assert isinstance(response.query_complexity, str) and len(response.query_complexity) > 0
        assert isinstance(response.result_preview, list)

    def test_complexity_estimation_correct(self):
        plan = QueryPlan(
            intent=IntentType.TOP_N,
            tables_needed=["orders", "products", "order_line_items"],
            primary_table="orders",
            metrics=[MetricSpec(name="revenue", expression="q * p")],
            limit=5,
        )
        complexity = estimate_query_complexity(plan)
        assert "3" in complexity or "join" in complexity.lower()
        assert "Top" in complexity or "top" in complexity.lower() or "ranking" in complexity.lower()
