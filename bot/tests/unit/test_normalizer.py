"""
Unit tests — bot/ingestion/normalizer.py
Tests: normalize_sheet_name, normalize_column_name, normalize_column_names, infer_and_cast_types
Also includes Property 1: Name Normalization Produces SQL-Safe Identifiers
"""
import re

import pandas as pd
import pytest
from hypothesis import given, settings as h_settings
from hypothesis import strategies as st

from bot.ingestion.normalizer import (
    infer_and_cast_types,
    normalize_column_name,
    normalize_column_names,
    normalize_sheet_name,
)

# ── Pattern for SQL-safe identifiers ─────────────────────────────────────────

_SQL_SAFE = re.compile(r"^[a-z0-9_]+$")


# ══════════════════════════════════════════════════════════════════════════════
# normalize_sheet_name
# ══════════════════════════════════════════════════════════════════════════════

class TestNormalizeSheetName:
    def test_spaces_to_underscores(self):
        assert normalize_sheet_name("Order Line Items") == "order_line_items"

    def test_lowercase(self):
        assert normalize_sheet_name("Products") == "products"

    def test_special_chars_removed(self):
        assert normalize_sheet_name("Q1 Revenue (USD)") == "q1_revenue_usd"

    def test_multiple_spaces_collapsed(self):
        result = normalize_sheet_name("  My  Sheet  ")
        assert "__" not in result
        assert not result.startswith("_")
        assert not result.endswith("_")

    def test_empty_string_returns_table(self):
        assert normalize_sheet_name("") == "table"

    def test_only_special_chars_returns_table(self):
        assert normalize_sheet_name("###") == "table"

    def test_already_normalized(self):
        assert normalize_sheet_name("orders") == "orders"

    def test_hyphens_to_underscores(self):
        assert normalize_sheet_name("order-line-items") == "order_line_items"

    def test_leading_trailing_underscores_stripped(self):
        result = normalize_sheet_name("__orders__")
        assert not result.startswith("_")
        assert not result.endswith("_")

    def test_numbers_preserved(self):
        assert "1" in normalize_sheet_name("Sheet1") or "sheet1" == normalize_sheet_name("Sheet1")

    def test_unicode_title(self):
        # Non-ASCII characters should be stripped
        result = normalize_sheet_name("Données ventes")
        assert _SQL_SAFE.match(result)


# ══════════════════════════════════════════════════════════════════════════════
# normalize_column_name
# ══════════════════════════════════════════════════════════════════════════════

class TestNormalizeColumnName:
    def test_created_at(self):
        assert normalize_column_name("Created At") == "created_at"

    def test_product_id(self):
        assert normalize_column_name("Product ID") == "product_id"

    def test_revenue_usd(self):
        assert normalize_column_name("Revenue (USD)") == "revenue_usd"

    def test_hash_prefix(self):
        result = normalize_column_name("#Orders")
        assert result.startswith("num")

    def test_empty_col(self):
        assert normalize_column_name("") == "col"

    def test_only_special(self):
        result = normalize_column_name("@!%")
        assert result  # non-empty
        assert _SQL_SAFE.match(result)


# ══════════════════════════════════════════════════════════════════════════════
# normalize_column_names (DataFrame)
# ══════════════════════════════════════════════════════════════════════════════

class TestNormalizeColumnNames:
    def test_multi_column_df(self):
        df = pd.DataFrame(columns=["Created At", "Product ID", "Revenue (USD)"])
        result = normalize_column_names(df)
        assert list(result.columns) == ["created_at", "product_id", "revenue_usd"]

    def test_duplicate_columns_get_suffixes(self):
        df = pd.DataFrame(columns=["value", "Value", "VALUE"])
        result = normalize_column_names(df)
        col_list = list(result.columns)
        assert len(set(col_list)) == len(col_list), "Duplicate column names not resolved"

    def test_original_data_preserved(self):
        df = pd.DataFrame({"Name": ["Alice", "Bob"], "Age": [30, 25]})
        result = normalize_column_names(df)
        assert list(result["name"]) == ["Alice", "Bob"]
        assert list(result["age"]) == [30, 25]


# ══════════════════════════════════════════════════════════════════════════════
# infer_and_cast_types
# ══════════════════════════════════════════════════════════════════════════════

class TestInferAndCastTypes:
    def test_date_column_parsed(self):
        df = pd.DataFrame({"created_at": ["2024-01-01", "2024-01-02", "2024-01-03"]})
        result = infer_and_cast_types(df)
        import pandas.api.types as pat
        assert pat.is_datetime64_any_dtype(result["created_at"])

    def test_id_column_integer(self):
        df = pd.DataFrame({"product_id": ["1", "2", "3", "4"]})
        result = infer_and_cast_types(df)
        import pandas.api.types as pat
        assert pat.is_integer_dtype(result["product_id"]) or str(result["product_id"].dtype).startswith("Int")

    def test_numeric_column_float(self):
        df = pd.DataFrame({"price": ["10.5", "20.0", "30.25", "40.0", "50.1"]})
        result = infer_and_cast_types(df)
        import pandas.api.types as pat
        assert pat.is_float_dtype(result["price"])

    def test_boolean_column(self):
        df = pd.DataFrame({"is_active": ["true", "false", "true", "true", "false"]})
        result = infer_and_cast_types(df)
        assert str(result["is_active"].dtype) == "boolean"

    def test_varchar_fallback(self):
        df = pd.DataFrame({"product_name": ["Widget A", "Gadget B", "Doohickey C"]})
        result = infer_and_cast_types(df)
        dtype_str = str(result["product_name"].dtype)
        assert result["product_name"].dtype == object or dtype_str in ("object", "string")

    def test_empty_df_unchanged(self):
        df = pd.DataFrame({"col": pd.Series([], dtype=object)})
        result = infer_and_cast_types(df)
        assert "col" in result.columns


# ══════════════════════════════════════════════════════════════════════════════
# Property 1: Name Normalization Produces SQL-Safe Identifiers
# ══════════════════════════════════════════════════════════════════════════════

@given(name=st.text(min_size=0, max_size=100))
@h_settings(max_examples=500)
def test_property1_sheet_name_always_sql_safe(name: str):
    """Property 1 (sheet): output is [a-z0-9_]+, no leading/trailing _, non-empty."""
    result = normalize_sheet_name(name)
    assert len(result) > 0, f"Empty result for input: {name!r}"
    assert _SQL_SAFE.match(result), f"Not SQL-safe: {result!r} (input: {name!r})"
    assert not result.startswith("_"), f"Starts with _: {result!r}"
    assert not result.endswith("_"), f"Ends with _: {result!r}"


@given(name=st.text(min_size=0, max_size=100))
@h_settings(max_examples=500)
def test_property1_column_name_always_sql_safe(name: str):
    """Property 1 (column): output is [a-z0-9_]+, no leading/trailing _, non-empty."""
    result = normalize_column_name(name)
    assert len(result) > 0, f"Empty result for input: {name!r}"
    assert _SQL_SAFE.match(result), f"Not SQL-safe: {result!r} (input: {name!r})"
    assert not result.startswith("_"), f"Starts with _: {result!r}"
    assert not result.endswith("_"), f"Ends with _: {result!r}"
