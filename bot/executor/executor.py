"""
bot/executor/executor.py — DuckDB Query Execution Layer.

execute_sql_safe(sql, conn)              → ExecutionResult
execute_sql_with_timeout(sql, conn, t)  → ExecutionResult
fetch_dataframe(sql, conn)              → pd.DataFrame
"""
from __future__ import annotations

import threading
import time
from typing import Optional

import duckdb
import pandas as pd
from loguru import logger

from bot.api.models import ExecutionResult
from bot.config import settings


def fetch_dataframe(
    sql: str,
    conn: duckdb.DuckDBPyConnection,
    max_rows: Optional[int] = None,
) -> pd.DataFrame:
    """Execute SQL and return result as DataFrame, capped at MAX_RESULT_ROWS.

    Args:
        sql:      Validated SQL string.
        conn:     Active DuckDB connection.
        max_rows: Override max rows (uses settings.max_result_rows by default).

    Returns:
        pandas DataFrame with results.
    """
    cap = max_rows or settings.max_result_rows
    capped_sql = f"SELECT * FROM ({sql}) AS _bot_result LIMIT {cap}"
    return conn.execute(capped_sql).fetchdf()


def execute_sql_safe(
    sql: str,
    conn: duckdb.DuckDBPyConnection,
) -> ExecutionResult:
    """Execute SQL and return ExecutionResult. Catches all exceptions.

    Args:
        sql:  Validated SQL string.
        conn: Active DuckDB connection.

    Returns:
        ExecutionResult with success=True and dataframe on success,
        or success=False and error_message on failure.
    """
    start = time.perf_counter()

    try:
        df = fetch_dataframe(sql, conn)
        elapsed_ms = (time.perf_counter() - start) * 1000

        logger.info(f"Query executed in {elapsed_ms:.1f}ms — {len(df)} rows returned")
        return ExecutionResult(
            success=True,
            dataframe=df,
            row_count=len(df),
            execution_time_ms=round(elapsed_ms, 2),
        )

    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        error_msg = str(exc)
        logger.error(f"Query execution failed ({elapsed_ms:.1f}ms): {error_msg}")
        return ExecutionResult(
            success=False,
            error_message=error_msg,
            execution_time_ms=round(elapsed_ms, 2),
        )


def execute_sql_with_timeout(
    sql: str,
    conn: duckdb.DuckDBPyConnection,
    timeout_seconds: Optional[int] = None,
) -> ExecutionResult:
    """Execute SQL with a timeout using threading.

    If the query exceeds `timeout_seconds`, returns a failure ExecutionResult
    with an appropriate error message.

    Args:
        sql:             Validated SQL string.
        conn:            Active DuckDB connection.
        timeout_seconds: Query timeout. Defaults to settings.max_query_timeout_seconds.

    Returns:
        ExecutionResult.
    """
    timeout = timeout_seconds or settings.max_query_timeout_seconds
    result_container: list[ExecutionResult] = []

    def _run() -> None:
        result_container.append(execute_sql_safe(sql, conn))

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    thread.join(timeout=timeout)

    if thread.is_alive():
        # Thread still running → timeout
        logger.error(f"Query timed out after {timeout}s")
        return ExecutionResult(
            success=False,
            error_message=f"Query timed out after {timeout} seconds. Consider simplifying your query.",
        )

    if not result_container:
        return ExecutionResult(
            success=False,
            error_message="Query execution produced no result (unknown error).",
        )

    return result_container[0]
