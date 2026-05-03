"""
bot/db.py — DuckDB singleton connection manager.
Provides get_connection() and close_connection() for use across all modules.
"""
from __future__ import annotations

import threading
from typing import Optional

import duckdb

from bot.config import settings


class _DuckDBManager:
    """Thread-safe DuckDB singleton connection manager."""

    def __init__(self) -> None:
        self._conn: Optional[duckdb.DuckDBPyConnection] = None
        self._lock = threading.Lock()

    def get_connection(self) -> duckdb.DuckDBPyConnection:
        """Return the shared DuckDB connection, creating it if necessary."""
        with self._lock:
            if self._conn is None:
                self._conn = duckdb.connect(settings.duckdb_path)
                # Enable progress bar for long queries (silent in production)
                self._conn.execute("SET threads TO 4;")
            return self._conn

    def close_connection(self) -> None:
        """Close the DuckDB connection and reset the singleton."""
        with self._lock:
            if self._conn is not None:
                try:
                    self._conn.close()
                except Exception:
                    pass
                finally:
                    self._conn = None

    def reset(self) -> None:
        """Alias for close_connection — clears all state."""
        self.close_connection()

    def is_connected(self) -> bool:
        """Check whether a live connection exists."""
        with self._lock:
            if self._conn is None:
                return False
            try:
                self._conn.execute("SELECT 1")
                return True
            except Exception:
                return False


# Global singleton
_manager = _DuckDBManager()


def get_connection() -> duckdb.DuckDBPyConnection:
    """Get the shared DuckDB connection."""
    return _manager.get_connection()


def close_connection() -> None:
    """Close and reset the DuckDB connection."""
    _manager.close_connection()


def is_connected() -> bool:
    """Check if DuckDB connection is alive."""
    return _manager.is_connected()
