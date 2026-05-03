"""
bot/api/models.py — All Pydantic v2 models for BOT.

Covers:
  - Schema Registry models (ColumnMetadata, TableMetadata, RelationshipMetadata, SchemaRegistry)
  - Query Plan models (QueryPlan, JoinPath, FilterSpec, MetricSpec)
  - Execution models (ValidationResult, ExecutionResult, IngestionResult)
  - API models (ChatRequest, ChatResponse, SchemaResponse, UploadResponse, HealthResponse)
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════════════════════
# Schema Registry Models
# ══════════════════════════════════════════════════════════════════════════════


class ColumnRole(str, Enum):
    PRIMARY_KEY = "primary_key"
    FOREIGN_KEY = "foreign_key"
    MEASURE = "measure"
    DIMENSION = "dimension"
    DATE = "date"
    UNKNOWN = "unknown"


class ColumnMetadata(BaseModel):
    name: str
    raw_name: str = ""
    sql_type: str  # DuckDB type string: INTEGER, VARCHAR, TIMESTAMP, etc.
    role: ColumnRole = ColumnRole.UNKNOWN
    sample_values: list[str] = Field(default_factory=list)  # Up to 5 sample values
    nullable: bool = True
    is_unique: bool = False
    null_pct: float = 0.0


class TableMetadata(BaseModel):
    table_name: str
    raw_sheet_name: str = ""
    description: str = ""
    columns: list[ColumnMetadata]
    row_count: int = 0
    col_count: int = 0
    primary_key_candidates: list[str] = Field(default_factory=list)
    date_columns: list[str] = Field(default_factory=list)
    metric_columns: list[str] = Field(default_factory=list)


class RelationshipMetadata(BaseModel):
    left_table: str
    left_column: str
    right_table: str
    right_column: str
    confidence: float = Field(ge=0.0, le=1.0)  # 1.0 = name match, <1.0 = value overlap
    relationship_type: str = "many_to_one"


class SchemaRegistry(BaseModel):
    tables: dict[str, TableMetadata] = Field(default_factory=dict)  # keyed by table_name
    relationships: list[RelationshipMetadata] = Field(default_factory=list)
    workbook_path: str = ""
    loaded_at: str = ""  # ISO timestamp

    def get_table(self, name: str) -> Optional[TableMetadata]:
        return self.tables.get(name)

    def get_column(self, table: str, column: str) -> Optional[ColumnMetadata]:
        t = self.get_table(table)
        if t is None:
            return None
        return next((c for c in t.columns if c.name == column), None)

    def table_names(self) -> list[str]:
        return list(self.tables.keys())

    def find_tables_by_column(self, col_name: str) -> list[str]:
        """Return all table names containing a column with the given name."""
        return [
            tname
            for tname, tmeta in self.tables.items()
            if any(c.name == col_name for c in tmeta.columns)
        ]


# ══════════════════════════════════════════════════════════════════════════════
# Query Plan Models
# ══════════════════════════════════════════════════════════════════════════════


class IntentType(str, Enum):
    LOOKUP = "lookup"
    AGGREGATION = "aggregation"
    COMPARISON = "comparison"
    TREND = "trend"
    TOP_N = "top_n"
    JOIN_BASED = "join_based"
    DERIVED_METRIC = "derived_metric"
    ANOMALY_DETECTION = "anomaly_detection"


class JoinPath(BaseModel):
    left_table: str
    left_column: str
    right_table: str
    right_column: str


class FilterSpec(BaseModel):
    table: str
    column: str
    operator: str  # eq, gt, lt, gte, lte, date_equals, date_range, in, like
    value: str


class MetricSpec(BaseModel):
    name: str
    expression: str  # SQL expression, e.g. "quantity * price"


class QueryPlan(BaseModel):
    intent: IntentType
    tables_needed: list[str]
    join_paths: list[JoinPath] = Field(default_factory=list)
    filters: list[FilterSpec] = Field(default_factory=list)
    metrics: list[MetricSpec] = Field(default_factory=list)
    group_by: list[str] = Field(default_factory=list)
    output_columns: list[str] = Field(default_factory=list)
    limit: Optional[int] = None  # Set for top_n intent
    time_column: Optional[str] = None  # Date column identified in schema for time filters
    primary_table: Optional[str] = None  # Main FROM table


# ══════════════════════════════════════════════════════════════════════════════
# Execution Models
# ══════════════════════════════════════════════════════════════════════════════


class ValidationResult(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)


class ExecutionResult(BaseModel):
    success: bool
    dataframe: Optional[Any] = None  # pd.DataFrame, excluded from serialization
    row_count: int = 0
    execution_time_ms: float = 0.0
    error_message: str = ""
    was_repaired: bool = False

    class Config:
        arbitrary_types_allowed = True


class IngestionResult(BaseModel):
    success: bool
    tables_loaded: list[str] = Field(default_factory=list)
    row_counts: dict[str, int] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)


# ══════════════════════════════════════════════════════════════════════════════
# API Models
# ══════════════════════════════════════════════════════════════════════════════


class ChatRequest(BaseModel):
    session_id: str = Field(default="default")
    message: str = Field(min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    answer: str
    sql: str = ""
    tables_used: list[str] = Field(default_factory=list)
    explanation: str = ""
    result_preview: list[dict] = Field(default_factory=list)
    query_complexity: str = ""
    was_repaired: bool = False
    error: Optional[str] = None


class SchemaResponse(BaseModel):
    tables: list[TableMetadata] = Field(default_factory=list)
    relationships: list[RelationshipMetadata] = Field(default_factory=list)


class UploadResponse(BaseModel):
    success: bool
    tables_loaded: list[str] = Field(default_factory=list)
    row_counts: dict[str, int] = Field(default_factory=dict)
    message: str = ""


class HealthResponse(BaseModel):
    status: str
    tables_loaded: int = 0
    duckdb_connected: bool = False
