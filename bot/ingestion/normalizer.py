"""
bot/ingestion/normalizer.py — Name normalization and type inference.

Functions:
  normalize_sheet_name(name)      → SQL-safe table name
  normalize_column_name(name)     → SQL-safe column name
  normalize_column_names(df)      → DataFrame with normalized columns
  infer_and_cast_types(df)        → DataFrame with correct dtypes
"""
from __future__ import annotations

import re
from typing import Any

import pandas as pd


# ── Constants ────────────────────────────────────────────────────────────────

# Patterns that suggest a timestamp / date column
_DATE_PATTERNS = re.compile(
    r"(^|_)(date|time|at|on|created|updated|timestamp|dt|day|month|year|ordered|shipped|delivered)($|_)",
    re.IGNORECASE,
)

# Patterns that suggest an integer / ID column
_ID_PATTERNS = re.compile(r"(^|_)id$", re.IGNORECASE)

# Patterns for numeric measures
_MEASURE_PATTERNS = re.compile(
    r"(quantity|qty|price|amount|total|count|revenue|cost|profit|sales|value|rate|fee|tax|discount)",
    re.IGNORECASE,
)

# Patterns for boolean columns
_BOOL_TRUE = {"true", "yes", "1", "t", "y"}
_BOOL_FALSE = {"false", "no", "0", "f", "n"}


# ── Name normalisation ───────────────────────────────────────────────────────


def normalize_sheet_name(name: str) -> str:
    """Convert an Excel sheet name to a SQL-safe table name.

    Rules:
      - Lowercase
      - Spaces / hyphens → underscore
      - Remove all non-alphanumeric characters except underscore
      - Collapse consecutive underscores to one
      - Strip leading / trailing underscores
      - Return 'table' if the result would be empty

    Examples:
      'Order Line Items' → 'order_line_items'
      'Q1 Revenue (USD)' → 'q1_revenue_usd'
      '  ##  '           → 'table'
    """
    if not isinstance(name, str):
        name = str(name)
    result = name.strip().lower()
    result = re.sub(r"[\s\-]+", "_", result)            # spaces/hyphens → _
    result = re.sub(r"[^a-z0-9_]", "", result)          # strip non-alnum
    result = re.sub(r"_+", "_", result)                 # collapse multiple _
    result = result.strip("_")                           # strip leading/trailing _
    return result if result else "table"


def normalize_column_name(name: str) -> str:
    """Convert a column header to a SQL-safe identifier.

    Examples:
      'Created At'     → 'created_at'
      'Product ID'     → 'product_id'
      'Revenue (USD)'  → 'revenue_usd'
      '#Orders'        → 'num_orders'
    """
    if not isinstance(name, str):
        name = str(name)
    result = name.strip().lower()
    # Replace '#' at the start with 'num_'
    result = re.sub(r"^#+", "num_", result)
    result = re.sub(r"[\s\-]+", "_", result)
    result = re.sub(r"[^a-z0-9_]", "", result)
    result = re.sub(r"_+", "_", result)
    result = result.strip("_")
    return result if result else "col"


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize all column names in a DataFrame to SQL-safe identifiers.

    Handles duplicate names by appending _1, _2 … suffixes.
    """
    new_names: list[str] = []
    seen: dict[str, int] = {}

    for col in df.columns:
        normalized = normalize_column_name(str(col))
        if normalized in seen:
            seen[normalized] += 1
            normalized = f"{normalized}_{seen[normalized]}"
        else:
            seen[normalized] = 0
        new_names.append(normalized)

    df = df.copy()
    df.columns = pd.Index(new_names)
    return df


# ── Type inference ───────────────────────────────────────────────────────────


def infer_and_cast_types(df: pd.DataFrame) -> pd.DataFrame:
    """Infer and cast column dtypes for DuckDB compatibility.

    Priority order per column:
      1. Name matches date pattern → try datetime parse
      2. Name matches _id pattern + values integer-like → integer
      3. >80% of non-null values are numeric → float / integer
      4. All non-null values in boolean set → boolean
      5. Default → keep as object (varchar in DuckDB)

    Returns a new DataFrame with corrected dtypes.
    """
    df = df.copy()

    for col in df.columns:
        series = df[col]

        # Skip columns that are already typed as numeric/datetime/boolean
        import pandas.api.types as pat
        if not (pat.is_object_dtype(series) or pat.is_string_dtype(series)):
            # Still attempt int-downcast on float columns with no decimal part
            if pat.is_float_dtype(series):
                non_null = series.dropna()
                if len(non_null) > 0 and (non_null == non_null.astype("int64", errors="ignore")).all():
                    try:
                        df[col] = series.astype("Int64")  # nullable integer
                    except Exception:
                        pass
            continue

        # 1. Date / timestamp heuristic
        if _DATE_PATTERNS.search(col):
            parsed = _try_parse_datetime(series)
            if parsed is not None:
                df[col] = parsed
                continue

        # 2. ID column → try integer
        if _ID_PATTERNS.search(col):
            parsed = _try_parse_integer(series)
            if parsed is not None:
                df[col] = parsed
                continue

        # 3. Numeric heuristic
        numeric_result = _try_parse_numeric(series)
        if numeric_result is not None:
            df[col] = numeric_result
            continue

        # 4. Boolean heuristic
        bool_result = _try_parse_boolean(series)
        if bool_result is not None:
            df[col] = bool_result
            continue

        # 5. Default: coerce to string, replacing NaN with None
        df[col] = series.where(series.notna(), other=None).astype(str).replace("None", None)

    return df


# ── Private helpers ──────────────────────────────────────────────────────────


def _try_parse_datetime(series: pd.Series) -> pd.Series | None:
    """Return a datetime Series if the column can be parsed as datetime."""
    non_null = series.dropna()
    if len(non_null) == 0:
        return None
    try:
        parsed = pd.to_datetime(series, infer_datetime_format=True, errors="coerce")
        # Accept if >70% of non-null values parsed successfully
        success_rate = parsed.notna().sum() / max(len(non_null), 1)
        if success_rate >= 0.7:
            return parsed
    except Exception:
        pass
    return None


def _try_parse_integer(series: pd.Series) -> pd.Series | None:
    """Return an integer Series if the column values look like integers."""
    non_null = series.dropna().astype(str).str.strip()
    if len(non_null) == 0:
        return None
    try:
        converted = pd.to_numeric(non_null, errors="coerce")
        success_rate = converted.notna().sum() / len(non_null)
        if success_rate >= 0.9:
            # Check they are integers (no decimal part)
            if (converted.dropna() == converted.dropna().astype("int64")).all():
                return pd.to_numeric(series, errors="coerce").astype("Int64")
    except Exception:
        pass
    return None


def _try_parse_numeric(series: pd.Series) -> pd.Series | None:
    """Return a numeric Series if >80% of non-null values are numeric."""
    non_null = series.dropna()
    if len(non_null) == 0:
        return None
    try:
        converted = pd.to_numeric(non_null.astype(str).str.replace(",", "", regex=False), errors="coerce")
        success_rate = converted.notna().sum() / len(non_null)
        if success_rate >= 0.8:
            full = pd.to_numeric(
                series.astype(str).str.replace(",", "", regex=False), errors="coerce"
            )
            # Downcast to integer if no decimal parts
            non_null_full = full.dropna()
            if len(non_null_full) > 0 and (non_null_full == non_null_full.astype("int64", errors="ignore")).all():
                return full.astype("Int64")
            return full  # float64
    except Exception:
        pass
    return None


def _try_parse_boolean(series: pd.Series) -> pd.Series | None:
    """Return a boolean Series if all non-null values are in a boolean set."""
    non_null = series.dropna().astype(str).str.strip().str.lower()
    if len(non_null) == 0:
        return None
    all_vals = set(non_null.unique())
    if all_vals.issubset(_BOOL_TRUE | _BOOL_FALSE):
        bool_series = series.astype(str).str.strip().str.lower().map(
            lambda v: True if v in _BOOL_TRUE else (False if v in _BOOL_FALSE else None)
        )
        return bool_series.astype("boolean")
    return None


def duckdb_type_for(series: pd.Series) -> str:
    """Map a pandas dtype to a DuckDB SQL type string."""
    dtype = series.dtype
    if pd.api.types.is_datetime64_any_dtype(dtype):
        return "TIMESTAMP"
    if pd.api.types.is_bool_dtype(dtype) or str(dtype) == "boolean":
        return "BOOLEAN"
    if pd.api.types.is_integer_dtype(dtype) or str(dtype) in ("Int8", "Int16", "Int32", "Int64"):
        return "INTEGER"
    if pd.api.types.is_float_dtype(dtype):
        return "DOUBLE"
    return "VARCHAR"
