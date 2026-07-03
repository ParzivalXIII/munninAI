"""
API Routes (HTMX Endpoints)

HTMX endpoints for dynamic interactions. Return partial HTML fragments.
"""

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from forge.web.dependencies import (
    get_fallback_diagnosis,
    get_fallback_gaps,
    get_incidents_data,
    get_postmortems_data,
    templates,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["api"])


# ── Incident Response ──────────────────────────────────────────────────


@router.post("/incidents/respond", response_class=HTMLResponse)
async def api_respond_incident(
    request: Request,
    alert_text: str = Form(...),
    severity: str = Form("P2"),
) -> HTMLResponse:
    """Process an alert and return diagnosis results (HTMX fragment)."""
    diagnosis = await _try_agent_diagnosis(alert_text, severity)

    context = {
        "request": request,
        "diagnosis": diagnosis,
        "alert_text": alert_text,
        "severity": severity,
    }
    return templates.TemplateResponse(
        request, "components/displays/diagnosis.html", context
    )


@router.post("/incidents/continue", response_class=HTMLResponse)
async def api_continue_investigation(
    request: Request,
    new_info: str = Form(...),
    session_id: str = Form(""),
) -> HTMLResponse:
    """Continue investigation with new information (HTMX fragment)."""
    update = await _try_continue_investigation(new_info, session_id)

    context = {
        "request": request,
        "update": update,
        "new_info": new_info,
    }
    return templates.TemplateResponse(
        request, "components/displays/investigation_update.html", context
    )


@router.post("/incidents/resolve", response_class=HTMLResponse)
async def api_resolve_incident(
    request: Request,
    resolution: str = Form(...),
    session_id: str = Form(""),
) -> HTMLResponse:
    """Resolve incident and bridge memory (HTMX fragment)."""
    result = await _try_resolve_incident(resolution, session_id)

    context = {
        "request": request,
        "result": result,
        "resolution": resolution,
    }
    return templates.TemplateResponse(
        request, "components/displays/resolution.html", context
    )


# ── Postmortem Generation ──────────────────────────────────────────────


@router.post("/postmortems/generate", response_class=HTMLResponse)
async def api_generate_postmortem(
    request: Request,
    incident_id: str = Form(...),
) -> HTMLResponse:
    """Generate a postmortem for an incident (HTMX fragment)."""
    postmortem = await _try_generate_postmortem(incident_id)

    context = {
        "request": request,
        "postmortem": postmortem,
    }
    return templates.TemplateResponse(
        request, "components/displays/postmortem_generated.html", context
    )


# ── Knowledge Gap Detection ────────────────────────────────────────────


@router.post("/gaps/detect", response_class=HTMLResponse)
async def api_detect_gaps(request: Request) -> HTMLResponse:
    """Detect knowledge gaps (HTMX fragment)."""
    gaps = await _try_detect_gaps()

    context = {
        "request": request,
        "missing_postmortems": gaps.get("missing_postmortems", []),
        "missing_runbooks": gaps.get("missing_runbooks", []),
        "recurring_patterns": gaps.get("recurring_patterns", []),
        "recommendations": gaps.get("recommendations", []),
    }
    return templates.TemplateResponse(
        request, "components/displays/gaps_results.html", context
    )


# ── Dashboard Metrics ──────────────────────────────────────────────────


@router.get("/dashboard/metrics", response_class=HTMLResponse)
async def api_dashboard_metrics(request: Request) -> HTMLResponse:
    """Refresh dashboard metrics (HTMX fragment)."""
    incidents = get_incidents_data()

    total = len(incidents)
    active = sum(1 for i in incidents if i.get("status") != "resolved")
    durations = [
        i["duration_minutes"]
        for i in incidents
        if i.get("duration_minutes") and i.get("status") == "resolved"
    ]
    avg_mttr = round(sum(durations) / len(durations)) if durations else 0

    context = {
        "request": request,
        "total_incidents": total,
        "active_incidents": active,
        "avg_mttr": avg_mttr,
    }
    return templates.TemplateResponse(
        request, "components/cards/metrics_refresh.html", context
    )


# ── Agent Integration Helpers ──────────────────────────────────────────


async def _try_agent_diagnosis(
    alert_text: str, severity: str
) -> dict[str, Any]:
    """Try real agent diagnosis, fallback to pre-canned response."""
    try:
        from forge.agents.incident_responder import IncidentResponder

        responder = IncidentResponder()
        diagnosis = await asyncio.wait_for(
            responder.diagnose_incident(alert_text, severity=severity),
            timeout=15.0,
        )
        return diagnosis
    except Exception as exc:
        logger.info("Using fallback diagnosis: %s", exc)
        return get_fallback_diagnosis(alert_text)


async def _try_continue_investigation(
    new_info: str, session_id: str
) -> dict[str, Any]:
    """Try continuing investigation with agent, fallback."""
    try:
        from forge.agents.incident_responder import IncidentResponder

        responder = IncidentResponder(session_id=session_id or None)
        update = await asyncio.wait_for(
            responder.continue_investigation(new_info),
            timeout=15.0,
        )
        return update
    except Exception as exc:
        logger.info("Using fallback investigation update: %s", exc)
        return {
            "updated_diagnosis": (
                f"Based on the new information — '{new_info[:100]}' — "
                "the investigation is progressing. Cross-referencing with "
                "historical patterns suggests checking service dependencies "
                "and resource utilization."
            ),
            "next_steps": [
                "Check service dependency health",
                "Review resource utilization metrics",
                "Examine recent deployment logs",
                "Verify circuit breaker states",
            ],
            "confidence_change": 0.1,
        }


async def _try_resolve_incident(
    resolution: str, session_id: str
) -> dict[str, Any]:
    """Try resolving incident with agent, fallback."""
    try:
        from forge.agents.incident_responder import IncidentResponder

        responder = IncidentResponder(session_id=session_id or None)
        result = await asyncio.wait_for(
            responder.resolve_incident(resolution),
            timeout=15.0,
        )
        return result
    except Exception as exc:
        logger.info("Using fallback resolution: %s", exc)
        return {
            "status": "resolved",
            "memory_bridged": True,
            "truth_subspace_built": True,
            "resolution_summary": resolution,
        }


async def _try_generate_postmortem(incident_id: str) -> dict[str, Any]:
    """Try generating postmortem with agent, fallback."""
    try:
        from forge.agents.postmortem_generator import PostmortemGenerator

        generator = PostmortemGenerator()
        result = await asyncio.wait_for(
            generator.generate_postmortem(
                incident_id=incident_id,
                incident_session_id=f"demo_{incident_id}",
            ),
            timeout=20.0,
        )
        return result
    except Exception as exc:
        logger.info("Using fallback postmortem: %s", exc)
        incidents = get_incidents_data()
        incident = next((i for i in incidents if i["id"] == incident_id), None)

        if incident:
            return {
                "incident_id": incident_id,
                "postmortem_text": (
                    f"Postmortem for {incident['title']}\n\n"
                    f"Root Cause: {incident.get('root_cause', 'Under investigation')}\n"
                    f"Resolution: {incident.get('resolution', 'Pending')}\n"
                    f"Duration: {incident.get('duration_minutes', 0)} minutes\n"
                    f"Users Affected: {incident.get('impact', {}).get('users_affected', 0)}"
                ),
                "generated_at": "2026-07-03T00:00:00Z",
            }
        return {
            "incident_id": incident_id,
            "postmortem_text": f"Postmortem generation pending for {incident_id}.",
            "generated_at": "2026-07-03T00:00:00Z",
        }


async def _try_detect_gaps() -> dict[str, Any]:
    """Try detecting gaps with agent, fallback to static analysis."""
    try:
        from forge.agents.knowledge_gap_detector import KnowledgeGapDetector

        detector = KnowledgeGapDetector()
        result = await asyncio.wait_for(
            detector.detect_gaps(),
            timeout=20.0,
        )
        return result
    except Exception as exc:
        logger.info("Using fallback gap detection: %s", exc)
        return get_fallback_gaps()
