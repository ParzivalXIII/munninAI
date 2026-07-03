"""
Postmortems Route

Postmortem list and detail views.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from forge.web.dependencies import (
    get_incidents_data,
    get_postmortems_data,
    templates,
)

router = APIRouter(prefix="/postmortems", tags=["postmortems"])


@router.get("", response_class=HTMLResponse)
async def postmortem_list(request: Request) -> HTMLResponse:
    """Render the postmortem list page."""
    postmortems = get_postmortems_data()
    incidents = get_incidents_data()

    # Build incident lookup for cross-referencing
    incident_lookup = {inc["id"]: inc for inc in incidents}

    # Enrich postmortems with incident data
    for pm in postmortems:
        inc = incident_lookup.get(pm.get("incident_id"))
        if inc:
            pm["incident_title"] = inc.get("title", "")
            pm["incident_timestamp"] = inc.get("timestamp", "")

    # Sort by date descending
    postmortems.sort(key=lambda x: x.get("date", ""), reverse=True)

    context = {
        "request": request,
        "postmortems": postmortems,
    }
    return templates.TemplateResponse(request, "pages/postmortems.html", context)


@router.get("/{postmortem_id}", response_class=HTMLResponse)
async def postmortem_detail(
    request: Request, postmortem_id: str
) -> HTMLResponse:
    """Render a single postmortem detail page."""
    postmortems = get_postmortems_data()
    pm = next((p for p in postmortems if p["id"] == postmortem_id), None)

    if not pm:
        context = {"request": request, "postmortems": [], "error": "Postmortem not found"}
        return templates.TemplateResponse(
            request, "pages/postmortems.html", context, status_code=404
        )

    # Get the related incident
    incidents = get_incidents_data()
    incident = next(
        (i for i in incidents if i["id"] == pm.get("incident_id")), None
    )

    context = {
        "request": request,
        "postmortem": pm,
        "incident": incident,
        "detail_view": True,
    }
    return templates.TemplateResponse(request, "pages/postmortem_detail.html", context)
