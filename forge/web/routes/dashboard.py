"""
Dashboard Route

Main dashboard showing metrics, recent incidents, and service health.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from forge.web.dependencies import (
    get_architecture_data,
    get_fallback_gaps,
    get_incidents_data,
    get_postmortems_data,
    templates,
)

router = APIRouter(tags=["dashboard"])


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    """Render the main dashboard page."""
    incidents = get_incidents_data()
    postmortems = get_postmortems_data()
    architecture = get_architecture_data()
    gaps = get_fallback_gaps()

    # ── Compute metrics ────────────────────────────────────────────
    total_incidents = len(incidents)
    active_incidents = sum(
        1 for inc in incidents if inc.get("status") != "resolved"
    )
    resolved_incidents = total_incidents - active_incidents

    # Average MTTR (mean time to resolve) in minutes
    durations = [
        inc["duration_minutes"]
        for inc in incidents
        if inc.get("duration_minutes") and inc.get("status") == "resolved"
    ]
    avg_mttr = round(sum(durations) / len(durations)) if durations else 0

    # Incidents by severity
    severity_counts: dict[str, int] = {"P1": 0, "P2": 0, "P3": 0, "P4": 0}
    for inc in incidents:
        sev = inc.get("severity", "P4")
        if sev in severity_counts:
            severity_counts[sev] += 1

    # Total revenue impact
    total_revenue_impact = sum(
        inc.get("impact", {}).get("revenue_impact_usd", 0) for inc in incidents
    )

    # Recent incidents (last 5)
    recent_incidents = sorted(
        incidents, key=lambda x: x.get("timestamp", ""), reverse=True
    )[:5]

    # Service health: count incidents per service
    services = architecture.get("services", [])
    service_incident_counts: dict[str, int] = {}
    for inc in incidents:
        for svc in inc.get("affected_services", []):
            service_incident_counts[svc] = service_incident_counts.get(svc, 0) + 1

    # Knowledge gap counts
    missing_postmortems_count = len(gaps.get("missing_postmortems", []))
    missing_runbooks_count = len(gaps.get("missing_runbooks", []))

    context = {
        "request": request,
        "total_incidents": total_incidents,
        "active_incidents": active_incidents,
        "resolved_incidents": resolved_incidents,
        "avg_mttr": avg_mttr,
        "severity_counts": severity_counts,
        "total_revenue_impact": total_revenue_impact,
        "recent_incidents": recent_incidents,
        "services": services,
        "service_incident_counts": service_incident_counts,
        "postmortems_count": len(postmortems),
        "missing_postmortems_count": missing_postmortems_count,
        "missing_runbooks_count": missing_runbooks_count,
        "total_users_affected": sum(
            inc.get("impact", {}).get("users_affected", 0) for inc in incidents
        ),
    }

    return templates.TemplateResponse(request, "pages/dashboard.html", context)
