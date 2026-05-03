"""
bot/validator/validator.py — SQL Validation and Safety Layer.

Uses sqlglot to parse and validate SQL before execution.
Enforces read-only access and schema reference correctness.
"""
from __future__ import annotations

from typing import Optional

import sqlglot
import sqlglot.expressions as exp
from loguru import logger

from bot.api.models import SchemaRegistry, ValidationResult


# ══════════════════════════════════════════════════════════════════════════════
# Custom exceptions
# ══════════════════════════════════════════════════════════════════════════════


class ReadOnlyViolationError(Exception):
    """Raised when SQL contains write operations."""


# ══════════════════════════════════════════════════════════════════════════════
# Write-operation node types to block
# ══════════════════════════════════════════════════════════════════════════════

_WRITE_NODE_TYPES = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Alter,
    exp.Create,
    exp.TruncateTable,
    exp.Merge,
    exp.Command,   # catches EXECUTE and other raw commands
)


# ══════════════════════════════════════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════════════════════════════════════


def enforce_read_only(sql: str) -> None:
    """Parse SQL and raise ReadOnlyViolationError if any write operations are found.

    Args:
        sql: SQL string to inspect.

    Raises:
        ReadOnlyViolationError: If INSERT, UPDATE, DELETE, DROP, ALTER, CREATE,
                                TRUNCATE, MERGE, or EXECUTE is detected.
    """
    try:
        parsed = sqlglot.parse(sql, dialect="duckdb")
    except sqlglot.errors.ParseError as exc:
        # Parse error is not a write violation — let it propagate as validation error
        raise ValueError(f"SQL parse error: {exc}") from exc

    for statement in parsed:
        if statement is None:
            continue
        for node in statement.walk():
            if isinstance(node, _WRITE_NODE_TYPES):
                op_type = type(node).__name__
                raise ReadOnlyViolationError(
                    f"Write operation detected: {op_type}. Only SELECT queries are allowed."
                )


def check_schema_references(
    sql: str,
    registry: SchemaRegistry,
) -> list[str]:
    """Extract all table and qualified column references from the SQL AST.

    Returns a list of error strings for any reference not found in the registry.
    Returns an empty list if all references are valid.
    """
    errors: list[str] = []

    try:
        parsed = sqlglot.parse(sql, dialect="duckdb")
    except sqlglot.errors.ParseError as exc:
        return [f"SQL parse error: {exc}"]

    known_tables = set(registry.table_names())

    # Collect aliased table references so we can resolve column refs
    alias_to_table: dict[str, str] = {}

    for statement in parsed:
        if statement is None:
            continue

        # Walk for table references
        for node in statement.walk():
            if isinstance(node, exp.Table):
                table_name = node.name
                if table_name and not _is_cte_name(statement, table_name):
                    if table_name not in known_tables:
                        errors.append(f"Unknown table: '{table_name}'")
                # Track alias
                alias = node.alias
                if alias and table_name:
                    alias_to_table[alias] = table_name

        # Walk for qualified column references (table.column or alias.column)
        for node in statement.walk():
            if isinstance(node, exp.Column):
                col_table = node.table
                col_name = node.name
                if col_table and col_name:
                    # Resolve alias → actual table name
                    actual_table = alias_to_table.get(col_table, col_table)
                    if actual_table in known_tables:
                        tmeta = registry.get_table(actual_table)
                        if tmeta:
                            col_names = {c.name for c in tmeta.columns}
                            if col_name not in col_names:
                                errors.append(
                                    f"Unknown column '{col_name}' in table '{actual_table}'. "
                                    f"Available: {sorted(col_names)}"
                                )

    return errors


def validate_sql(
    sql: str,
    registry: SchemaRegistry,
) -> ValidationResult:
    """Full validation pipeline: parse → read-only check → schema reference check.

    Args:
        sql:      SQL string to validate.
        registry: SchemaRegistry to validate references against.

    Returns:
        ValidationResult(valid=True) or ValidationResult(valid=False, errors=[...])
    """
    errors: list[str] = []

    # Step 1: Basic length / emptiness check
    if not sql or not sql.strip():
        return ValidationResult(valid=False, errors=["SQL is empty"])

    # Step 2: Syntax check + read-only enforcement
    try:
        enforce_read_only(sql)
    except ReadOnlyViolationError as exc:
        logger.warning(f"Read-only violation: {exc}")
        return ValidationResult(valid=False, errors=[str(exc)])
    except ValueError as exc:
        errors.append(str(exc))
        return ValidationResult(valid=False, errors=errors)

    # Step 3: Schema reference check
    ref_errors = check_schema_references(sql, registry)
    errors.extend(ref_errors)

    if errors:
        logger.warning(f"SQL validation errors: {errors}")
        return ValidationResult(valid=False, errors=errors)

    logger.debug("SQL validation passed")
    return ValidationResult(valid=True)


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════


def _is_cte_name(statement: exp.Expression, name: str) -> bool:
    """Return True if the given name is defined as a CTE in this statement."""
    with_clause = statement.find(exp.With)
    if not with_clause:
        return False
    for cte in with_clause.find_all(exp.CTE):
        if cte.alias == name or cte.alias_or_name == name:
            return True
    return False
