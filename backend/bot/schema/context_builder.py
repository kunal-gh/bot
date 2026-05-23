"""
bot/schema/context_builder.py — Build compact schema context strings for LLM prompts.

build_schema_context_for_llm(registry) → str
"""
from __future__ import annotations

from bot.api.models import ColumnRole, SchemaRegistry


def build_schema_context_for_llm(registry: SchemaRegistry) -> str:
    """Build a compact but complete schema summary for LLM prompts.

    Format per table:
        TABLE table_name (N rows)
          COLUMNS:
            col1 [TYPE, role] samples: [v1, v2, v3]
            ...
          PRIMARY KEY: col
          DATE COLUMNS: col_a, col_b
          METRIC COLUMNS: col_c, col_d

        RELATIONSHIPS:
          table_a.col → table_b.col (confidence: 0.98)
    """
    if not registry.tables:
        return "No tables loaded. Please upload an Excel workbook first."

    lines: list[str] = ["=== DATABASE SCHEMA ===", ""]

    for tname, tmeta in registry.tables.items():
        lines.append(f"TABLE: {tname} ({tmeta.row_count:,} rows, {tmeta.col_count} columns)")
        lines.append("  COLUMNS:")

        for col in tmeta.columns:
            role_str = f", {col.role.value}" if col.role != ColumnRole.UNKNOWN else ""
            sample_str = ""
            if col.sample_values:
                sample_str = f" samples: [{', '.join(col.sample_values[:3])}]"
            lines.append(f"    {col.name} [{col.sql_type}{role_str}]{sample_str}")

        if tmeta.primary_key_candidates:
            lines.append(f"  PRIMARY KEY: {', '.join(tmeta.primary_key_candidates)}")
        if tmeta.date_columns:
            lines.append(f"  DATE COLUMNS: {', '.join(tmeta.date_columns)}")
        if tmeta.metric_columns:
            lines.append(f"  METRIC COLUMNS: {', '.join(tmeta.metric_columns)}")
        lines.append("")

    if registry.relationships:
        lines.append("=== RELATIONSHIPS ===")
        for rel in registry.relationships:
            lines.append(
                f"  {rel.left_table}.{rel.left_column} → "
                f"{rel.right_table}.{rel.right_column} "
                f"(confidence: {rel.confidence:.2f})"
            )
        lines.append("")

    return "\n".join(lines)


def build_compact_schema(registry: SchemaRegistry, max_tables: int = 10) -> str:
    """Build an ultra-compact single-line-per-table schema for tight prompts."""
    lines: list[str] = []
    for tname, tmeta in list(registry.tables.items())[:max_tables]:
        col_parts = []
        for col in tmeta.columns:
            col_parts.append(f"{col.name}:{col.sql_type}")
        lines.append(f"TABLE {tname} ({', '.join(col_parts)})")
        if tmeta.primary_key_candidates:
            lines[-1] += f" [PK: {tmeta.primary_key_candidates[0]}]"
    for rel in registry.relationships[:20]:
        lines.append(
            f"FK {rel.left_table}.{rel.left_column} → {rel.right_table}.{rel.right_column}"
        )
    return "\n".join(lines)
