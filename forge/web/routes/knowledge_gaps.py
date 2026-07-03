"""
Knowledge Gaps Route

Knowledge gap analysis and recommendations.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from forge.web.dependencies import get_fallback_gaps, templates

router = APIRouter(tags=["knowledge_gaps"])


@router.get("/gaps", response_class=HTMLResponse)
async def knowledge_gaps_page(request: Request) -> HTMLResponse:
    """Render the knowledge gap analysis page."""
    gaps = get_fallback_gaps()

    context = {
        "request": request,
        "missing_postmortems": gaps.get("missing_postmortems", []),
        "missing_runbooks": gaps.get("missing_runbooks", []),
        "recurring_patterns": gaps.get("recurring_patterns", []),
        "recommendations": gaps.get("recommendations", []),
    }
    return templates.TemplateResponse(request, "pages/knowledge_gaps.html", context)
