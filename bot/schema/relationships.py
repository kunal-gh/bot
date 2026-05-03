"""
bot/schema/relationships.py — Foreign key relationship inference.

detect_relationships(registry) → list[RelationshipMetadata]
"""
from __future__ import annotations

import re

import duckdb
from loguru import logger

from bot.api.models import RelationshipMetadata, SchemaRegistry


_ID_SUFFIX = re.compile(r"_id$", re.IGNORECASE)


def detect_relationships(
    registry: SchemaRegistry,
    conn: duckdb.DuckDBPyConnection | None = None,
) -> list[RelationshipMetadata]:
    """Infer FK relationships between tables by:

    1. Column name matching: if table_a.col_name == table_b.col_name
       and col ends in '_id' → confidence=1.0
    2. Table-name prefix matching: col 'order_id' in 'line_items'
       → points to 'orders.order_id' → confidence=1.0
    3. Value overlap (requires conn): sample 100 rows from each table,
       check intersection ratio > 0.5 → confidence=ratio

    Returns deduplicated list of RelationshipMetadata sorted by confidence desc.
    """
    table_names = registry.table_names()
    relationships: list[RelationshipMetadata] = []
    seen: set[tuple[str, str, str, str]] = set()

    def _add(left_table, left_col, right_table, right_col, confidence):
        key = (left_table, left_col, right_table, right_col)
        rev_key = (right_table, right_col, left_table, left_col)
        if key in seen or rev_key in seen:
            return
        seen.add(key)
        relationships.append(
            RelationshipMetadata(
                left_table=left_table,
                left_column=left_col,
                right_table=right_table,
                right_column=right_col,
                confidence=round(confidence, 4),
                relationship_type="many_to_one",
            )
        )

    # Build a lookup: column_name → [(table_name, column)]
    col_to_tables: dict[str, list[str]] = {}
    for tname in table_names:
        tmeta = registry.get_table(tname)
        if not tmeta:
            continue
        for col in tmeta.columns:
            col_to_tables.setdefault(col.name, []).append(tname)

    # Strategy 1 & 2: column name matching for _id columns
    for tname in table_names:
        tmeta = registry.get_table(tname)
        if not tmeta:
            continue
        for col in tmeta.columns:
            if not _ID_SUFFIX.search(col.name):
                continue  # Only foreign-key candidates

            # Strategy 1: same column name exists in another table
            for other_table in col_to_tables.get(col.name, []):
                if other_table == tname:
                    continue
                other_meta = registry.get_table(other_table)
                if not other_meta:
                    continue
                other_col = next(
                    (c for c in other_meta.columns if c.name == col.name), None
                )
                if other_col and other_col.is_unique:
                    _add(tname, col.name, other_table, col.name, 1.0)
                    logger.debug(
                        f"Relationship (name match): {tname}.{col.name} → {other_table}.{col.name}"
                    )

            # Strategy 2: table-prefix matching
            # e.g., 'order_id' in 'line_items' → try 'orders' table
            prefix = _ID_SUFFIX.sub("", col.name)  # 'order_id' → 'order'
            for candidate_table in [prefix, prefix + "s"]:
                if candidate_table == tname or candidate_table not in table_names:
                    continue
                cand_meta = registry.get_table(candidate_table)
                if not cand_meta:
                    continue
                # Look for matching column in candidate (same name or 'id')
                for target_col_name in [col.name, "id"]:
                    cand_col = next(
                        (c for c in cand_meta.columns if c.name == target_col_name),
                        None,
                    )
                    if cand_col and cand_col.is_unique:
                        _add(tname, col.name, candidate_table, target_col_name, 1.0)
                        logger.debug(
                            f"Relationship (prefix match): {tname}.{col.name} → "
                            f"{candidate_table}.{target_col_name}"
                        )

    # Strategy 3: value-overlap sampling (only if conn provided)
    if conn is not None:
        _add_value_overlap_relationships(registry, conn, seen, relationships)

    # Sort by confidence descending
    relationships.sort(key=lambda r: r.confidence, reverse=True)
    return relationships


def _add_value_overlap_relationships(
    registry: SchemaRegistry,
    conn: duckdb.DuckDBPyConnection,
    seen: set,
    relationships: list[RelationshipMetadata],
) -> None:
    """Add relationships based on value overlap between columns."""
    table_names = registry.table_names()

    for i, left_table in enumerate(table_names):
        for right_table in table_names[i + 1 :]:
            left_meta = registry.get_table(left_table)
            right_meta = registry.get_table(right_table)
            if not left_meta or not right_meta:
                continue

            for lcol in left_meta.columns:
                for rcol in right_meta.columns:
                    if lcol.name != rcol.name:
                        continue
                    # Skip if already captured via name-matching
                    key = (left_table, lcol.name, right_table, rcol.name)
                    rev = (right_table, rcol.name, left_table, lcol.name)
                    if key in seen or rev in seen:
                        continue
                    # Check value overlap
                    ratio = _value_overlap_ratio(conn, left_table, lcol.name, right_table, rcol.name)
                    if ratio > 0.5:
                        seen.add(key)
                        relationships.append(
                            RelationshipMetadata(
                                left_table=left_table,
                                left_column=lcol.name,
                                right_table=right_table,
                                right_column=rcol.name,
                                confidence=round(ratio, 4),
                                relationship_type="many_to_one",
                            )
                        )
                        logger.debug(
                            f"Relationship (value overlap {ratio:.2f}): "
                            f"{left_table}.{lcol.name} ↔ {right_table}.{rcol.name}"
                        )


def _value_overlap_ratio(
    conn: duckdb.DuckDBPyConnection,
    left_table: str,
    left_col: str,
    right_table: str,
    right_col: str,
    sample_size: int = 100,
) -> float:
    """Compute the intersection ratio between two column value samples."""
    try:
        left_vals_result = conn.execute(
            f'SELECT DISTINCT CAST("{left_col}" AS VARCHAR) '
            f'FROM "{left_table}" WHERE "{left_col}" IS NOT NULL LIMIT {sample_size}'
        ).fetchall()
        right_vals_result = conn.execute(
            f'SELECT DISTINCT CAST("{right_col}" AS VARCHAR) '
            f'FROM "{right_table}" WHERE "{right_col}" IS NOT NULL LIMIT {sample_size}'
        ).fetchall()

        left_vals = {r[0] for r in left_vals_result}
        right_vals = {r[0] for r in right_vals_result}

        if not left_vals or not right_vals:
            return 0.0

        intersection = len(left_vals & right_vals)
        union = len(left_vals | right_vals)
        return intersection / max(union, 1)
    except Exception as e:
        logger.debug(f"Value overlap check failed ({left_table}.{left_col} ↔ {right_table}.{right_col}): {e}")
        return 0.0
