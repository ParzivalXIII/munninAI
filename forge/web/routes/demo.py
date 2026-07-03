"""
Demo Mode Route

Guided walkthrough for hackathon judges.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from forge.web.dependencies import templates

router = APIRouter(tags=["demo"])


@router.get("/demo", response_class=HTMLResponse)
async def demo_page(request: Request) -> HTMLResponse:
    """Render the guided demo mode page."""
    context = {
        "request": request,
        "acts": [
            {
                "number": 1,
                "title": "Build the Brain",
                "description": (
                    "MunninAI ingests your DevOps knowledge into a persistent "
                    "memory layer. Watch as we load 15 incidents, 10 services, "
                    "and 6 postmortems into the knowledge graph."
                ),
                "target_url": "/",
                "icon": "brain",
                "key_moment": (
                    "Notice how MunninAI already knows about your infrastructure."
                ),
            },
            {
                "number": 2,
                "title": "The Morning After",
                "description": (
                    "It's 9 AM. Three alerts fired overnight. Let's ask "
                    "MunninAI what happened. Watch it reconstruct the incident "
                    "timeline from memory."
                ),
                "target_url": "/incidents/respond",
                "icon": "alert",
                "key_moment": (
                    "MunninAI didn't just find the issue — it reconstructed "
                    "the entire incident timeline from memory."
                ),
            },
            {
                "number": 3,
                "title": "Self-Improvement",
                "description": (
                    "Now let's resolve the incident and watch MunninAI learn. "
                    "The session memory gets bridged into permanent knowledge, "
                    "making future diagnoses faster."
                ),
                "target_url": "/incidents/respond",
                "icon": "sparkle",
                "key_moment": (
                    "MunninAI just got smarter. The next incident like this "
                    "will be diagnosed in seconds, not minutes."
                ),
            },
            {
                "number": 4,
                "title": "Knowledge Gaps",
                "description": (
                    "Let's see what MunninAI knows about our knowledge base. "
                    "It identifies missing postmortems, absent runbooks, and "
                    "recurring patterns."
                ),
                "target_url": "/gaps",
                "icon": "search",
                "key_moment": (
                    "MunninAI doesn't just remember — it tells you what "
                    "you're missing."
                ),
            },
            {
                "number": 5,
                "title": "The Pitch",
                "description": (
                    "MunninAI turns your team's collective amnesia into "
                    "institutional memory. Built on Cognee Cloud's hybrid "
                    "graph-vector memory layer, it's the AI that never forgets."
                ),
                "target_url": "/",
                "icon": "rocket",
                "key_moment": (
                    "Your AI just woke up in Vegas with no memory of last "
                    "night. MunninAI makes sure that never happens."
                ),
            },
        ],
    }
    return templates.TemplateResponse(request, "pages/demo.html", context)
