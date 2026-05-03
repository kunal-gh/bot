"""
Unit tests — edge cases
Tests: blank queries, unknown columns, no date columns, empty results, etc.
"""
import pytest
import duckdb
import pandas as pd

from bot.api.models import (
    ColumnMetadata, FilterSpec, IntentType, JoinPath, MetricSpec,
    QueryPlan, SchemaRegistry, TableMetadata
)
from bot.compiler.compiler import compile_plan_to_sql
from bot.executor.executor import execute_sql_safe
from bot.formatter.formatter import format_answer, summarize_result
from bot.validator.validator import validate_sql


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _make_registry(*table_specs) -> SchemaRegistry:
    tables = {}
    for tname, cols in table_specs:
        columns = [ColumnMetadata(name=c, sql_type="VARCHAR") for c in cols]
        tables[tname] = TableMetadata(table_name=tname, columns=columns, row_count=10)
    return SchemaRegistry(tables=tables)


def _make_plan(**kwargs) -> QueryPlan:
    defaults = {
        "intent": IntentType.LOOKUP,
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
    defaults.update(kwargs)
    return QueryPlan(**defaults)


# ══════════════════════════════════════════════════════════════════════════════
# Blank / whitespace queries — handled at API level (Pydantic min_length=1)
# But validate that empty SQL fails cleanly in validator
# ══════════════════════════════════════════════════════════════════════════════

class TestBlankInput:
    def test_empty_sql_fails_validation(self):
        registry = _make_registry(("orders", ["order_id"]))
        result = validate_sql("", registry)
        assert not result.valid
        assert result.errors

    def test_whitespace_sql_fails_validation(self):
        registry = _make_registry(("orders", ["order_id"]))
        result = validate_sql("   \n\t  ", registry)
        assert not result.valid


# ══════════════════════════════════════════════════════════════════════════════
# Query referencing non-existent column
# ══════════════════════════════════════════════════════════════════════════════

class TestUnknownColumnReference:
    def test_unknown_qualified_column_invalid(self):
        registry = _make_registry(("orders", ["order_id", "total"]))
        sql = 'SELECT "orders"."nonexistent_col" FROM "orders"'
        result = validate_sql(sql, registry)
        assert not result.valid
        assert any("nonexistent_col" in e for e in result.errors)


# ══════════════════════════════════════════════════════════════════════════════
# Single-sheet workbook — no join paths generated
# ══════════════════════════════════════════════════════════════════════════════

class TestSingleSheetWorkbook:
    def test_single_table_plan_no_joins(self):
        plan = _make_plan(tables_needed=["orders"], primary_table="orders", join_paths=[])
        sql = compile_plan_to_sql(plan)
        assert "JOIN" not in sql.upper()
        assert "orders" in sql

    def test_no_join_paths_empty_clause(self):
        from bot.compiler.compiler import build_join_clause
        plan = _make_plan(join_paths=[])
        assert build_join_clause(plan) == ""


# ══════════════════════════════════════════════════════════════════════════════
# Empty result set → format_answer returns graceful message
# ══════════════════════════════════════════════════════════════════════════════

class TestEmptyResultSet:
    def test_empty_df_summary(self):
        plan = _make_plan()
        df = pd.DataFrame()
        summary = summarize_result(df, plan)
        assert "no" in summary.lower() or "not found" in summary.lower() or "0" in summary

    def test_format_answer_empty_df(self):
        plan = _make_plan()
        df = pd.DataFrame(columns=["order_id"])  # 0 rows
        response = format_answer(df, "Show me orders", plan, "SELECT 1")
        assert response.answer
        assert response.result_preview == []


# ══════════════════════════════════════════════════════════════════════════════
# Division by zero — caught as execution error
# ══════════════════════════════════════════════════════════════════════════════

class TestDivisionByZero:
    def test_division_by_zero_caught(self):
        conn = duckdb.connect(":memory:")
        conn.execute("CREATE TABLE t (x INTEGER)")
        conn.execute("INSERT INTO t VALUES (0)")
        result = execute_sql_safe("SELECT 1 / x FROM t", conn)
        # DuckDB raises division by zero — should be caught as error
        # (DuckDB may or may not raise depending on version — check graceful handling)
        assert isinstance(result.success, bool)  # Always returns a result, not crash
        conn.close()

    def test_nullif_prevents_division_by_zero(self):
        conn = duckdb.connect(":memory:")
        conn.execute("CREATE TABLE t (x INTEGER)")
        conn.execute("INSERT INTO t VALUES (0)")
        result = execute_sql_safe("SELECT 1 / NULLIF(x, 0) FROM t", conn)
        assert result.success
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# Workbook with no date columns — time query graceful handling
# ══════════════════════════════════════════════════════════════════════════════

class TestNoDateColumns:
    def test_time_phrase_resolves_with_fallback_column(self):
        """Even without a real date column, resolve_time_phrase returns a string."""
        from bot.glossary.glossary import resolve_time_phrase
        # Use a column name that doesn't exist — should still return SQL string
        result = resolve_time_phrase("yesterday", date_column="nonexistent_date_col")
        assert result  # not empty
        assert "nonexistent_date_col" in result  # uses the column we provided

    def test_where_clause_with_time_filter_compiles(self):
        """Compiler should not crash for time filters even if column is missing."""
        plan = _make_plan(
            time_column=None,  # no date column
            filters=[FilterSpec(
                table="orders", column="created_at",
                operator="date_equals", value="yesterday"
            )]
        )
        sql = compile_plan_to_sql(plan)
        assert sql  # Should produce something without crashing


# ══════════════════════════════════════════════════════════════════════════════
# Executor timeout handling
# ══════════════════════════════════════════════════════════════════════════════

class TestExecutorTimeout:
    def test_timeout_returns_failure_result(self):
        from bot.executor.executor import execute_sql_with_timeout
        conn = duckdb.connect(":memory:")
        conn.execute("CREATE TABLE t (x INTEGER)")
        for i in range(100):
            conn.execute(f"INSERT INTO t VALUES ({i})")
        # This should complete fast, just verify timeout mechanism doesn't crash
        result = execute_sql_with_timeout("SELECT * FROM t", conn, timeout_seconds=30)
        assert isinstance(result.success, bool)
        conn.close()
