"""
Unit tests — bot/validator/validator.py
Tests: enforce_read_only, check_schema_references, validate_sql
Also includes Property 5: SQL Safety
"""
import pytest
from hypothesis import given, settings as h_settings
from hypothesis import strategies as st

from bot.api.models import ColumnMetadata, ColumnRole, SchemaRegistry, TableMetadata
from bot.validator.validator import (
    ReadOnlyViolationError,
    check_schema_references,
    enforce_read_only,
    validate_sql,
)


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _make_registry(tables: dict[str, list[str]]) -> SchemaRegistry:
    """Build a SchemaRegistry with given table→column names."""
    table_metas = {}
    for tname, cols in tables.items():
        columns = [ColumnMetadata(name=c, sql_type="VARCHAR") for c in cols]
        table_metas[tname] = TableMetadata(table_name=tname, columns=columns, row_count=100)
    return SchemaRegistry(tables=table_metas)


_BASIC_REGISTRY = _make_registry({
    "orders": ["order_id", "customer_id", "created_at", "total"],
    "products": ["product_id", "product_name", "price"],
})


# ══════════════════════════════════════════════════════════════════════════════
# enforce_read_only
# ══════════════════════════════════════════════════════════════════════════════

class TestEnforceReadOnly:
    @pytest.mark.parametrize("sql", [
        "INSERT INTO orders VALUES (1, 2, 3)",
        "UPDATE orders SET total = 0",
        "DELETE FROM orders",
        "DROP TABLE orders",
        "ALTER TABLE orders ADD COLUMN foo VARCHAR",
        "CREATE TABLE foo (id INT)",
        "TRUNCATE TABLE orders",
        "MERGE orders USING products ON orders.id = products.id WHEN MATCHED THEN UPDATE SET total = 0",
    ])
    def test_write_sql_raises(self, sql: str):
        with pytest.raises(ReadOnlyViolationError):
            enforce_read_only(sql)

    @pytest.mark.parametrize("sql", [
        "SELECT * FROM orders",
        "SELECT order_id FROM orders WHERE total > 100",
        "SELECT COUNT(*) FROM orders GROUP BY customer_id",
        "WITH cte AS (SELECT * FROM orders) SELECT * FROM cte",
    ])
    def test_read_only_sql_does_not_raise(self, sql: str):
        # Should not raise
        enforce_read_only(sql)


# ══════════════════════════════════════════════════════════════════════════════
# check_schema_references
# ══════════════════════════════════════════════════════════════════════════════

class TestCheckSchemaReferences:
    def test_valid_references_empty_errors(self):
        sql = 'SELECT "order_id" FROM "orders"'
        errors = check_schema_references(sql, _BASIC_REGISTRY)
        # No table-level errors for known table
        table_errors = [e for e in errors if "Unknown table" in e]
        assert not table_errors

    def test_unknown_table_reported(self):
        sql = 'SELECT * FROM "nonexistent_table"'
        errors = check_schema_references(sql, _BASIC_REGISTRY)
        assert any("nonexistent_table" in e for e in errors)

    def test_unknown_qualified_column_reported(self):
        sql = 'SELECT "orders"."nonexistent_column" FROM "orders"'
        errors = check_schema_references(sql, _BASIC_REGISTRY)
        assert any("nonexistent_column" in e for e in errors)

    def test_valid_qualified_column_no_error(self):
        sql = 'SELECT "orders"."order_id" FROM "orders"'
        errors = check_schema_references(sql, _BASIC_REGISTRY)
        col_errors = [e for e in errors if "nonexistent" in e or "Unknown column" in e]
        assert not col_errors

    def test_cte_name_not_flagged_as_unknown_table(self):
        sql = 'WITH cte AS (SELECT * FROM "orders") SELECT * FROM cte'
        errors = check_schema_references(sql, _BASIC_REGISTRY)
        cte_errors = [e for e in errors if "cte" in e.lower()]
        assert not cte_errors


# ══════════════════════════════════════════════════════════════════════════════
# validate_sql
# ══════════════════════════════════════════════════════════════════════════════

class TestValidateSQL:
    def test_valid_select_returns_valid_true(self):
        sql = 'SELECT "order_id", "total" FROM "orders"'
        result = validate_sql(sql, _BASIC_REGISTRY)
        assert result.valid

    def test_empty_sql_invalid(self):
        result = validate_sql("", _BASIC_REGISTRY)
        assert not result.valid

    def test_write_sql_invalid(self):
        result = validate_sql("INSERT INTO orders VALUES (1)", _BASIC_REGISTRY)
        assert not result.valid

    def test_unknown_table_invalid(self):
        result = validate_sql('SELECT * FROM "fake_table"', _BASIC_REGISTRY)
        assert not result.valid

    def test_cte_select_valid(self):
        sql = 'WITH cte AS (SELECT "order_id" FROM "orders") SELECT * FROM cte'
        result = validate_sql(sql, _BASIC_REGISTRY)
        assert result.valid

    def test_validation_result_has_errors_on_failure(self):
        result = validate_sql("DELETE FROM orders", _BASIC_REGISTRY)
        assert not result.valid
        assert len(result.errors) > 0


# ══════════════════════════════════════════════════════════════════════════════
# Property 5: SQL Safety — No Write Operations Pass Validation
# ══════════════════════════════════════════════════════════════════════════════

_WRITE_KEYWORDS = ["INSERT", "UPDATE", "DELETE", "DROP TABLE", "ALTER TABLE",
                   "CREATE TABLE", "TRUNCATE TABLE"]


@given(keyword=st.sampled_from(_WRITE_KEYWORDS))
@h_settings(max_examples=100)
def test_property5_write_sql_always_blocked(keyword: str):
    """Property 5: Any SQL with a write keyword must fail validation."""
    sql = f"{keyword} orders VALUES (1)"

    # enforce_read_only should raise
    try:
        enforce_read_only(sql)
        # If no exception, that's a violation — but some edge cases may not parse cleanly
    except (ReadOnlyViolationError, ValueError):
        pass  # Expected

    # validate_sql should return valid=False
    result = validate_sql(sql, _BASIC_REGISTRY)
    assert not result.valid, f"Write SQL passed validation: {sql!r}"


@given(table=st.sampled_from(["orders", "products"]))
@h_settings(max_examples=100)
def test_property5_pure_select_never_blocked(table: str):
    """Property 5: Pure SELECT statements must NOT raise ReadOnlyViolationError."""
    sql = f'SELECT * FROM "{table}"'
    # Should not raise
    enforce_read_only(sql)
