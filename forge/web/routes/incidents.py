"""
Incidents Route

Incident list and detail views.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from forge.web.dependencies import get_incidents_data, templates

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("", response_class=HTMLResponse)
async def incident_list(
    request: Request,
    severity: str | None = None,
    status: str | None = None,
    service: str | None = None,
) -> HTMLResponse:
    """Render the incident list page with optional filters."""
    incidents = get_incidents_data()

    # Apply filters
    if severity:
        incidents = [i for i in incidents if i.get("severity") == severity]
    if status:
        incidents = [i for i in incidents if i.get("status") == status]
    if service:
        incidents = [
            i
            for i in incidents
            if service in i.get("affected_services", [])
        ]

    # Sort by timestamp descending
    incidents.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    # Collect unique values for filter dropdowns
    all_incidents = get_incidents_data()
    severities = sorted({i.get("severity", "") for i in all_incidents})
    statuses = sorted({i.get("status", "") for i in all_incidents})
    all_services: set[str] = set()
    for inc in all_incidents:
        all_services.update(inc.get("affected_services", []))
    services_list = sorted(all_services)

    context = {
        "request": request,
        "incidents": incidents,
        "severity": severity,
        "status": status,
        "service": service,
        "severities": severities,
        "statuses": statuses,
        "services": services_list,
    }

    return templates.TemplateResponse(request, "pages/incidents.html", context)


@router.get("/{incident_id}", response_class=HTMLResponse)
async def incident_detail(request: Request, incident_id: str) -> HTMLResponse:
    """Render incident detail page."""
    incidents = get_incidents_data()
    incident = next((i for i in incidents if i["id"] == incident_id), None)

    if not incident:
        return templates.TemplateResponse(
            request,
            "pages/incidents.html",
            {"request": request, "incidents": [], "error": "Incident not found"},
            status_code=404,
        )

    context = {
        "request": request,
        "incident": incident,
        "detail_view": True,
    }

    return templates.TemplateResponse(request, "pages/incident_detail.html", context)
