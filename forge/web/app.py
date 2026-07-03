"""
MunninAI Web Application

FastAPI web interface for the DevOps intelligence platform.
Serves Jinja2 templates with HTMX for dynamic interactions.
"""

from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from forge.web.dependencies import STATIC_DIR

logger = structlog.get_logger(__name__)

# ── FastAPI Application ────────────────────────────────────────────────
app = FastAPI(
    title="MunninAI",
    description="DevOps Intelligence Platform — The AI That Never Forgets",
    version="0.1.0",
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Register routers (imported after app creation to avoid circular imports)
from forge.web.routes import (  # noqa: E402
    api,
    dashboard,
    demo,
    incidents,
    incident_response,
    knowledge_gaps,
    postmortems,
)

app.include_router(dashboard.router)
app.include_router(incident_response.router)  # Must be before incidents router
app.include_router(incidents.router)
app.include_router(postmortems.router)
app.include_router(knowledge_gaps.router)
app.include_router(demo.router)
app.include_router(api.router)


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy", "service": "munnin-ai-web"}
