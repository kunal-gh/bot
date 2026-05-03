"""
bot/api/routes.py — FastAPI route handlers.

Endpoints:
  POST /upload      — Upload and load a new Excel workbook
  POST /reload-data — Reload current workbook
  GET  /schema      — Return current SchemaRegistry
  GET  /health      — Health check
  POST /chat        — Main chat endpoint (full pipeline)
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from loguru import logger

from bot.api.models import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    SchemaResponse,
    UploadResponse,
)
from bot.compiler.compiler import compile_plan_to_sql
from bot.db import get_connection, is_connected
from bot.executor.executor import execute_sql_with_timeout
from bot.formatter.formatter import format_answer
from bot.glossary.glossary import build_glossary_context
from bot.ingestion.loader import refresh_dataset
from bot.planner.planner import LLMClient, build_query_plan
from bot.planner.validator import PlanningError
from bot.repair.repair import repair_sql, retry_execution
from bot.schema.context_builder import build_schema_context_for_llm
from bot.schema.registry import build_schema_registry
from bot.schema.relationships import detect_relationships
from bot.validator.validator import ReadOnlyViolationError, validate_sql

router = APIRouter()


# ══════════════════════════════════════════════════════════════════════════════
# Shared application state (simple in-process store)
# ══════════════════════════════════════════════════════════════════════════════

class _AppState:
    """Lightweight in-process state store."""
    schema_registry = None
    current_workbook_path: Optional[str] = None
    llm_client: Optional[LLMClient] = None


state = _AppState()


def _get_llm_client() -> LLMClient:
    """Return cached LLM client, creating it if needed."""
    if state.llm_client is None:
        from bot.config import settings
        state.llm_client = LLMClient(
            api_key=settings.openai_api_key,
            model=settings.llm_model,
            base_url=settings.llm_base_url,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )
    return state.llm_client


def _rebuild_schema() -> None:
    """Rebuild SchemaRegistry and detect relationships."""
    conn = get_connection()
    registry = build_schema_registry(conn)
    registry.relationships = detect_relationships(registry, conn)
    if state.current_workbook_path:
        registry.workbook_path = state.current_workbook_path
    state.schema_registry = registry
    logger.info(
        f"Schema rebuilt: {len(registry.tables)} tables, "
        f"{len(registry.relationships)} relationships"
    )


# ══════════════════════════════════════════════════════════════════════════════
# Endpoints
# ══════════════════════════════════════════════════════════════════════════════


@router.post("/upload", response_model=UploadResponse)
async def upload_workbook(file: UploadFile = File(...)) -> UploadResponse:
    """Upload an Excel workbook and load all its sheets into DuckDB."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in (".xlsx", ".xls"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {suffix}. Please upload .xlsx or .xls"
        )

    # Save to temp file
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    # Ingest
    conn = get_connection()
    result = refresh_dataset(tmp_path, conn)

    if not result.success:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load workbook: {'; '.join(result.errors)}"
        )

    state.current_workbook_path = tmp_path
    _rebuild_schema()

    return UploadResponse(
        success=True,
        tables_loaded=result.tables_loaded,
        row_counts=result.row_counts,
        message=f"Successfully loaded {len(result.tables_loaded)} tables from '{file.filename}'",
    )


@router.post("/reload-data", response_model=UploadResponse)
async def reload_data() -> UploadResponse:
    """Reload the currently loaded workbook from disk."""
    if not state.current_workbook_path:
        raise HTTPException(
            status_code=400,
            detail="No workbook currently loaded. Please upload one first."
        )

    conn = get_connection()
    result = refresh_dataset(state.current_workbook_path, conn)

    if not result.success:
        raise HTTPException(
            status_code=500,
            detail=f"Reload failed: {'; '.join(result.errors)}"
        )

    _rebuild_schema()

    return UploadResponse(
        success=True,
        tables_loaded=result.tables_loaded,
        row_counts=result.row_counts,
        message=f"Reloaded {len(result.tables_loaded)} tables successfully.",
    )


@router.get("/schema", response_model=SchemaResponse)
async def get_schema() -> SchemaResponse:
    """Return the current SchemaRegistry."""
    if state.schema_registry is None:
        raise HTTPException(
            status_code=400,
            detail="No workbook loaded. Please upload an Excel file first."
        )
    return SchemaResponse(
        tables=list(state.schema_registry.tables.values()),
        relationships=state.schema_registry.relationships,
    )


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Return system health status."""
    connected = is_connected()
    table_count = len(state.schema_registry.tables) if state.schema_registry else 0
    return HealthResponse(
        status="healthy" if connected else "degraded",
        tables_loaded=table_count,
        duckdb_connected=connected,
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Main chat endpoint — full pipeline execution.

    Pipeline:
      1. Validate workbook is loaded
      2. Build schema context + glossary context
      3. LLM → QueryPlan (JSON plan)
      4. Compile plan → SQL
      5. Validate SQL (read-only + schema refs)
      6. Execute in DuckDB
      7. On failure: repair SQL once and retry
      8. Format result → ChatResponse
    """
    # Guard: workbook must be loaded
    if state.schema_registry is None or not state.schema_registry.tables:
        raise HTTPException(
            status_code=400,
            detail="No workbook loaded. Please upload an Excel file before querying."
        )

    query = request.message.strip()
    logger.info(f"[{request.session_id}] Query: {query!r}")

    conn = get_connection()
    registry = state.schema_registry
    llm = _get_llm_client()

    # Step 2: Build context
    schema_context = build_schema_context_for_llm(registry)
    glossary_context = build_glossary_context()

    # Step 3: Plan
    try:
        plan = build_query_plan(query, schema_context, glossary_context, llm)
    except PlanningError as exc:
        logger.error(f"Planning failed: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Could not understand the query: {exc}"
        )

    # Step 4: Compile
    sql = compile_plan_to_sql(plan)
    logger.info(f"Compiled SQL:\n{sql}")

    # Step 5: Validate
    try:
        validation = validate_sql(sql, registry)
    except ReadOnlyViolationError as exc:
        raise HTTPException(status_code=403, detail=str(exc))

    if not validation.valid:
        # Attempt repair immediately if compilation produced bad SQL
        logger.warning(f"Validation failed: {validation.errors} — attempting repair")
        try:
            fixed_sql = repair_sql(sql, "; ".join(validation.errors), schema_context, plan, llm)
            result = retry_execution(fixed_sql, registry, conn)
        except Exception as repair_exc:
            return ChatResponse(
                answer="I was unable to generate a valid query for this question.",
                error=f"Validation failed: {'; '.join(validation.errors)}. Repair also failed: {repair_exc}",
                tables_used=plan.tables_needed,
                query_complexity="Error",
            )
        if not result.success:
            return ChatResponse(
                answer="I could not complete this query after repair.",
                error=result.error_message,
                tables_used=plan.tables_needed,
                query_complexity="Error",
                was_repaired=True,
            )
        return format_answer(result.dataframe, query, plan, fixed_sql, llm, was_repaired=True)

    # Step 6: Execute
    result = execute_sql_with_timeout(sql, conn)

    # Step 7: Repair on execution failure
    if not result.success:
        logger.warning(f"Execution failed: {result.error_message} — attempting repair")
        try:
            fixed_sql = repair_sql(sql, result.error_message, schema_context, plan, llm)
            result = retry_execution(fixed_sql, registry, conn)
        except Exception as repair_exc:
            return ChatResponse(
                answer="The query failed and repair was unsuccessful.",
                error=f"Original error: {result.error_message}. Repair failed: {repair_exc}",
                sql=sql,
                tables_used=plan.tables_needed,
                query_complexity=_complexity(plan),
            )

        if not result.success:
            return ChatResponse(
                answer=f"I tried to answer your question but encountered an error: {result.error_message}",
                error=result.error_message,
                sql=sql,
                tables_used=plan.tables_needed,
                query_complexity=_complexity(plan),
                was_repaired=True,
            )
        return format_answer(result.dataframe, query, plan, fixed_sql, llm, was_repaired=True)

    # Step 8: Format successful result
    return format_answer(result.dataframe, query, plan, sql, llm)


def _complexity(plan) -> str:
    from bot.formatter.formatter import estimate_query_complexity
    return estimate_query_complexity(plan)
