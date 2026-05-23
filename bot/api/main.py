"""
bot/api/main.py — FastAPI application entry point.

Run with: uvicorn bot.api.main:app --reload --port 8000
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from bot.api.routes import router, state, _rebuild_schema
from bot.config import settings
from bot.db import get_connection, close_connection
from bot.ingestion.loader import refresh_dataset


# ══════════════════════════════════════════════════════════════════════════════
# Lifespan
# ══════════════════════════════════════════════════════════════════════════════


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    logger.info("BOT starting up...")

    # Validate config (will raise RuntimeError if LLM key missing for openai)
    try:
        settings.validate_on_startup()
    except RuntimeError as e:
        logger.warning(f"Config warning: {e}")

    # Initialize DuckDB connection
    conn = get_connection()
    logger.info("DuckDB connection established")

    # Optionally pre-load default workbook
    if settings.workbook_path:
        try:
            result = refresh_dataset(settings.workbook_path, conn)
            if result.success:
                state.current_workbook_path = settings.workbook_path
                _rebuild_schema()
                logger.info(
                    f"Pre-loaded workbook '{settings.workbook_path}' — "
                    f"{len(result.tables_loaded)} tables"
                )
            else:
                logger.warning(f"Could not pre-load workbook: {result.errors}")
        except Exception as e:
            logger.warning(f"Workbook pre-load skipped: {e}")

    logger.info("BOT startup complete. Ready to serve requests.")
    yield

    # Shutdown
    logger.info("BOT shutting down...")
    close_connection()
    logger.info("DuckDB connection closed. Goodbye.")


# ══════════════════════════════════════════════════════════════════════════════
# App construction
# ══════════════════════════════════════════════════════════════════════════════


app = FastAPI(
    title="BOT — Universal Excel Analytics Chatbot",
    description=(
        "A schema-aware analytical chatbot that converts natural language questions "
        "into validated SQL executed over any Excel workbook."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend clients from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routes
app.include_router(router)


# ══════════════════════════════════════════════════════════════════════════════
# Root endpoint
# ══════════════════════════════════════════════════════════════════════════════


@app.get("/")
async def root():
    return {
        "name": "BOT — Universal Excel Analytics Chatbot",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }
