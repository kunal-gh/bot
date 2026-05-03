"""
bot/ingestion/loader.py — Excel workbook loading and DuckDB registration.

Functions:
  load_workbook(path)                → {table_name: DataFrame}
  store_to_duckdb(df, name, conn)   → None
  refresh_dataset(path, conn)       → IngestionResult
"""
from __future__ import annotations

import time
from pathlib import Path

import duckdb
import pandas as pd
from loguru import logger

from bot.api.models import IngestionResult
from bot.ingestion.normalizer import (
    infer_and_cast_types,
    normalize_column_names,
    normalize_sheet_name,
)


def load_workbook(path: str) -> dict[str, pd.DataFrame]:
    """Load all sheets from an .xlsx or .xls file.

    Returns:
        dict mapping normalized_table_name → normalized DataFrame.
    Raises:
        FileNotFoundError if the path does not exist.
        ValueError if the file is not a supported Excel format.
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Workbook not found: {path}")
    if file_path.suffix.lower() not in (".xlsx", ".xls"):
        raise ValueError(f"Unsupported file format: {file_path.suffix}")

    logger.info(f"Loading workbook: {path}")
    try:
        raw_sheets: dict[str, pd.DataFrame] = pd.read_excel(
            path,
            sheet_name=None,          # load ALL sheets
            engine="openpyxl",
            dtype=object,             # read everything as object; we handle types ourselves
        )
    except Exception as e:
        raise ValueError(f"Failed to read Excel file '{path}': {e}") from e

    result: dict[str, pd.DataFrame] = {}
    for raw_name, df in raw_sheets.items():
        table_name = normalize_sheet_name(raw_name)
        logger.debug(f"  Sheet '{raw_name}' → table '{table_name}' ({len(df)} rows)")

        # Drop fully-empty rows and columns
        df = df.dropna(how="all").dropna(axis=1, how="all").reset_index(drop=True)

        df = normalize_column_names(df)
        df = infer_and_cast_types(df)

        # Store the original sheet name as metadata attribute (best-effort)
        df.attrs["raw_sheet_name"] = raw_name

        result[table_name] = df

    logger.info(f"Loaded {len(result)} tables from workbook")
    return result


def store_to_duckdb(
    df: pd.DataFrame,
    table_name: str,
    conn: duckdb.DuckDBPyConnection,
) -> None:
    """Register a DataFrame as a DuckDB table, replacing any existing table.

    Uses CREATE OR REPLACE TABLE … AS SELECT … for full materialisation,
    which ensures the table persists across connection re-uses.
    """
    try:
        # Register as a temporary view first so we can SELECT from it
        conn.register(f"_tmp_{table_name}", df)
        conn.execute(
            f'CREATE OR REPLACE TABLE "{table_name}" AS SELECT * FROM "_tmp_{table_name}"'
        )
        conn.unregister(f"_tmp_{table_name}")
        logger.debug(f"Stored table '{table_name}' ({len(df)} rows) in DuckDB")
    except Exception as e:
        logger.error(f"Failed to store table '{table_name}': {e}")
        raise


def _drop_all_user_tables(conn: duckdb.DuckDBPyConnection) -> None:
    """Drop all non-system tables from the DuckDB connection."""
    try:
        existing = conn.execute("SHOW TABLES").fetchdf()
        for tname in existing.get("name", pd.Series()).tolist():
            conn.execute(f'DROP TABLE IF EXISTS "{tname}"')
            logger.debug(f"Dropped existing table: {tname}")
    except Exception as e:
        logger.warning(f"Could not drop existing tables: {e}")


def refresh_dataset(path: str, conn: duckdb.DuckDBPyConnection) -> IngestionResult:
    """Full reload: drop existing tables, re-ingest all sheets, return result.

    This is called both on initial load and on /reload-data requests.
    """
    start = time.time()
    errors: list[str] = []

    # Step 1: Drop all existing tables
    _drop_all_user_tables(conn)

    # Step 2: Load workbook
    try:
        sheets = load_workbook(path)
    except Exception as e:
        logger.error(f"Workbook load failed: {e}")
        return IngestionResult(success=False, errors=[str(e)])

    # Step 3: Store each sheet into DuckDB
    loaded: list[str] = []
    row_counts: dict[str, int] = {}

    for table_name, df in sheets.items():
        try:
            store_to_duckdb(df, table_name, conn)
            loaded.append(table_name)
            row_counts[table_name] = len(df)
        except Exception as e:
            err = f"Failed to load table '{table_name}': {e}"
            logger.error(err)
            errors.append(err)

    elapsed = time.time() - start
    logger.info(
        f"Dataset refresh complete in {elapsed:.2f}s — "
        f"{len(loaded)} tables loaded, {len(errors)} errors"
    )

    return IngestionResult(
        success=len(loaded) > 0,
        tables_loaded=loaded,
        row_counts=row_counts,
        errors=errors,
    )
