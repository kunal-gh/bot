"""
bot/schema/registry.py — Schema Intelligence Layer.

build_schema_registry(conn) → SchemaRegistry
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

import duckdb
import pandas as pd
from loguru import logger

from bot.api.models import (
    ColumnMetadata,
    ColumnRole,
    SchemaRegistry,
    TableMetadata,
)


# ── Column role detection patterns ───────────────────────────────────────────

_PK_PATTERNS = re.compile(r"(^|_)(id)$", re.IGNORECASE)
_FK_PATTERNS = re.compile(r"_id$", re.IGNORECASE)
_DATE_PATTERNS = re.compile(
    r"(date|time|at|on|created|updated|timestamp|dt|day|month|year|ordered|shipped|delivered)",
    re.IGNORECASE,
)
_MEASURE_PATTERNS = re.compile(
    r"(quantity|qty|price|amount|total|count|revenue|cost|profit|sales|value|rate|fee|tax|discount|margin)",
    re.IGNORECASE,
)

# DuckDB types that map to dates
_DATE_TYPES = {"TIMESTAMP", "DATE", "TIMESTAMP WITH TIME ZONE", "TIMESTAMPTZ"}


def _infer_column_role(
    col_name: str,
    sql_type: str,
    is_unique: bool,
    table_name: str,
) -> ColumnRole:
    """Heuristically determine the semantic role of a column."""
    upper_type = sql_type.upper()

    # Date columns
    if upper_type in _DATE_TYPES or _DATE_PATTERNS.search(col_name):
        return ColumnRole.DATE

    # Primary key: name is exactly 'id' or '<table>_id' and values are unique
    if is_unique and _PK_PATTERNS.search(col_name):
        return ColumnRole.PRIMARY_KEY

    # Foreign key: ends in _id but not the PK
    if _FK_PATTERNS.search(col_name) and not is_unique:
        return ColumnRole.FOREIGN_KEY

    # Measure columns
    if _MEASURE_PATTERNS.search(col_name) and upper_type in ("INTEGER", "DOUBLE", "FLOAT", "BIGINT", "DECIMAL"):
        return ColumnRole.MEASURE

    # Dimension (categorical string)
    if upper_type in ("VARCHAR", "TEXT", "STRING"):
        return ColumnRole.DIMENSION

    return ColumnRole.UNKNOWN


def build_schema_registry(conn: duckdb.DuckDBPyConnection) -> SchemaRegistry:
    """Inspect all tables in DuckDB and build the SchemaRegistry.

    Steps:
      1. SHOW TABLES to get all table names
      2. DESCRIBE each table to get column names and types
      3. Sample up to 5 distinct values per column
      4. Compute basic statistics (uniqueness, null %)
      5. Classify column roles
      6. Detect primary keys, date columns, metric columns

    Returns:
        SchemaRegistry populated with all table metadata.
    """
    registry = SchemaRegistry(
        loaded_at=datetime.now(tz=timezone.utc).isoformat()
    )

    try:
        tables_df = conn.execute("SHOW TABLES").fetchdf()
    except Exception as e:
        logger.error(f"Could not list tables: {e}")
        return registry

    table_names = tables_df.get("name", pd.Series()).tolist()
    logger.info(f"Building schema registry for {len(table_names)} tables")

    for tname in table_names:
        try:
            table_meta = _build_table_metadata(conn, tname)
            registry.tables[tname] = table_meta
            logger.debug(
                f"  Registered table '{tname}': "
                f"{len(table_meta.columns)} columns, {table_meta.row_count} rows"
            )
        except Exception as e:
            logger.error(f"Failed to inspect table '{tname}': {e}")

    return registry


def _build_table_metadata(
    conn: duckdb.DuckDBPyConnection,
    table_name: str,
) -> TableMetadata:
    """Build TableMetadata for a single DuckDB table."""

    # Row count
    row_count_result = conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()
    row_count = int(row_count_result[0]) if row_count_result else 0

    # Column descriptions
    describe_df = conn.execute(f'DESCRIBE "{table_name}"').fetchdf()

    columns: list[ColumnMetadata] = []
    date_cols: list[str] = []
    metric_cols: list[str] = []
    pk_candidates: list[str] = []

    for _, row in describe_df.iterrows():
        col_name = str(row.get("column_name", row.get("Field", "")))
        col_type = str(row.get("column_type", row.get("Type", "VARCHAR"))).upper()
        nullable = str(row.get("null", row.get("Null", "YES"))).upper() != "NO"

        # Sample values
        sample_values = _get_sample_values(conn, table_name, col_name)

        # Uniqueness check
        is_unique = _check_uniqueness(conn, table_name, col_name, row_count)

        # Null percentage
        null_count_result = conn.execute(
            f'SELECT COUNT(*) FROM "{table_name}" WHERE "{col_name}" IS NULL'
        ).fetchone()
        null_count = int(null_count_result[0]) if null_count_result else 0
        null_pct = null_count / max(row_count, 1)

        role = _infer_column_role(col_name, col_type, is_unique, table_name)

        col_meta = ColumnMetadata(
            name=col_name,
            sql_type=col_type,
            role=role,
            sample_values=sample_values,
            nullable=nullable,
            is_unique=is_unique,
            null_pct=round(null_pct, 4),
        )
        columns.append(col_meta)

        # Classify into groups
        if role == ColumnRole.DATE or col_type in _DATE_TYPES:
            date_cols.append(col_name)
        if role == ColumnRole.MEASURE:
            metric_cols.append(col_name)
        if role == ColumnRole.PRIMARY_KEY:
            pk_candidates.append(col_name)

    # Fallback: if no PK found, check for columns named 'id' or matching table_id pattern
    if not pk_candidates:
        for col in columns:
            if col.name in ("id", f"{table_name}_id") and col.is_unique:
                pk_candidates.append(col.name)

    return TableMetadata(
        table_name=table_name,
        columns=columns,
        row_count=row_count,
        col_count=len(columns),
        primary_key_candidates=pk_candidates,
        date_columns=date_cols,
        metric_columns=metric_cols,
    )


def _get_sample_values(
    conn: duckdb.DuckDBPyConnection,
    table_name: str,
    col_name: str,
    limit: int = 5,
) -> list[str]:
    """Sample up to `limit` distinct non-null values from a column."""
    try:
        rows = conn.execute(
            f'SELECT DISTINCT "{col_name}" FROM "{table_name}" '
            f'WHERE "{col_name}" IS NOT NULL LIMIT {limit}'
        ).fetchall()
        return [str(r[0]) for r in rows]
    except Exception:
        return []


def _check_uniqueness(
    conn: duckdb.DuckDBPyConnection,
    table_name: str,
    col_name: str,
    row_count: int,
) -> bool:
    """Return True if the column has all unique values."""
    if row_count == 0:
        return True
    try:
        result = conn.execute(
            f'SELECT COUNT(DISTINCT "{col_name}") FROM "{table_name}"'
        ).fetchone()
        distinct = int(result[0]) if result else 0
        return distinct == row_count
    except Exception:
        return False
