"""
Incident Response Route

Chat interface for real-time incident diagnosis with the Incident Responder agent.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from forge.web.dependencies import templates

router = APIRouter(tags=["incident_response"])


@router.get("/incidents/respond", response_class=HTMLResponse)
async def incident_response_page(request: Request) -> HTMLResponse:
    """Render the incident response chat interface."""
    context = {
        "request": request,
    }
    return templates.TemplateResponse(request, "pages/incident_response.html", context)
