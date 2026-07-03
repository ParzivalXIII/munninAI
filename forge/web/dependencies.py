"""
Web Dependencies

Shared data loaders, template engine, and fallback responses.
Separated from app.py to avoid circular imports.
"""

import json
from pathlib import Path

import structlog
from fastapi.templating import Jinja2Templates

logger = structlog.get_logger(__name__)

# ── Paths ──────────────────────────────────────────────────────────────
WEB_DIR = Path(__file__).parent
TEMPLATES_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"
DATA_DIR = Path(__file__).parent.parent.parent / "data"

# ── Jinja2 ─────────────────────────────────────────────────────────────
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# ── Data helpers ───────────────────────────────────────────────────────
def _load_json(filename: str) -> dict:
    """Load a JSON file from the data directory."""
    filepath = DATA_DIR / filename
    try:
        with open(filepath, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        logger.warning("Failed to load data file", file=filename, error=str(exc))
        return {}


def get_incidents_data() -> list[dict]:
    """Load incidents from JSON."""
    data = _load_json("incidents.json")
    return data.get("incidents", [])


def get_architecture_data() -> dict:
    """Load architecture from JSON."""
    data = _load_json("architecture.json")
    return {
        "services": data.get("services", []),
        "teams": data.get("teams", []),
        "runbooks": data.get("runbooks", []),
        "infrastructure": data.get("infrastructure", {}),
    }


def get_postmortems_data() -> list[dict]:
    """Load postmortems from JSON."""
    data = _load_json("postmortems.json")
    return data.get("postmortems", [])


def get_fallback_diagnosis(alert_text: str) -> dict:
    """Return a pre-canned diagnosis when Cognee is unavailable."""
    alert_lower = alert_text.lower()
    if "connection" in alert_lower or "pool" in alert_lower:
        return {
            "diagnosis": (
                "Based on historical incident patterns, this appears to be a "
                "connection pool exhaustion issue. Similar incidents (INC-001, INC-006) "
                "were caused by insufficient pool sizing for traffic volume."
            ),
            "root_cause": (
                "PostgreSQL connection pool size insufficient for current traffic volume. "
                "Historical data shows this pattern recurs when traffic exceeds 3x baseline."
            ),
            "confidence": 0.85,
            "similar_incidents": [
                {
                    "id": "INC-001",
                    "title": "Payments Service Connection Pool Exhaustion",
                    "severity": "P1",
                    "similarity": 0.92,
                },
                {
                    "id": "INC-006",
                    "title": "Payments Service Connection Pool Exhaustion (Recurrence)",
                    "severity": "P1",
                    "similarity": 0.88,
                },
            ],
            "resolution_steps": [
                "Check current connection pool utilization: pg_stat_activity",
                "Increase pool size if above 80% utilization",
                "Enable connection pool monitoring alerts",
                "Consider adding read replicas for query offloading",
            ],
        }
    if "memory" in alert_lower or "oom" in alert_lower:
        return {
            "diagnosis": (
                "Memory-related incident detected. Historical patterns suggest either "
                "a memory leak or insufficient memory limits for traffic volume."
            ),
            "root_cause": (
                "Memory limits may be too low for current workload, or a memory leak "
                "exists in the affected service."
            ),
            "confidence": 0.75,
            "similar_incidents": [
                {
                    "id": "INC-002",
                    "title": "Auth Service Memory Leak",
                    "severity": "P2",
                    "similarity": 0.85,
                },
                {
                    "id": "INC-012",
                    "title": "Kubernetes Pod OOM Kills During Traffic Spike",
                    "severity": "P1",
                    "similarity": 0.80,
                },
            ],
            "resolution_steps": [
                "Check memory usage: kubectl top pods",
                "Review recent deployments for memory leaks",
                "Increase memory limits if needed",
                "Configure HPA for memory-based scaling",
            ],
        }
    return {
        "diagnosis": (
            "Analyzing the alert against historical incident patterns. "
            "Checking knowledge graph for similar incidents and known resolution paths."
        ),
        "root_cause": "Under investigation. More data needed for accurate diagnosis.",
        "confidence": 0.5,
        "similar_incidents": [
            {
                "id": "INC-015",
                "title": "Cascading Failure from Search Service Memory Leak",
                "severity": "P1",
                "similarity": 0.45,
            }
        ],
        "resolution_steps": [
            "Gather more information about the affected service",
            "Check service dependencies and recent deployments",
            "Review monitoring dashboards for anomalies",
        ],
    }


def get_fallback_gaps() -> dict:
    """Return pre-computed knowledge gaps from JSON data."""
    incidents = get_incidents_data()
    postmortems = get_postmortems_data()
    architecture = get_architecture_data()

    pm_incident_ids = {pm["incident_id"] for pm in postmortems}
    missing_pms = [inc for inc in incidents if inc["id"] not in pm_incident_ids]

    runbook_services = {rb["service"] for rb in architecture.get("runbooks", [])}
    missing_runbooks = [
        svc
        for svc in architecture.get("services", [])
        if svc["name"] not in runbook_services
    ]

    return {
        "missing_postmortems": missing_pms,
        "missing_runbooks": missing_runbooks,
        "recurring_patterns": [
            {
                "pattern": "Connection pool exhaustion",
                "occurrences": 2,
                "incidents": ["INC-001", "INC-006"],
            },
            {
                "pattern": "Memory leaks causing OOM kills",
                "occurrences": 2,
                "incidents": ["INC-002", "INC-015"],
            },
            {
                "pattern": "Insufficient capacity planning before traffic spikes",
                "occurrences": 3,
                "incidents": ["INC-001", "INC-012", "INC-006"],
            },
        ],
        "recommendations": [
            {
                "priority": "high",
                "action": f"Create postmortems for {len(missing_pms)} incidents without documentation",
                "rationale": "Undocumented incidents cannot be learned from",
                "effort": "medium",
            },
            {
                "priority": "high",
                "action": f"Write runbooks for {len(missing_runbooks)} services without them",
                "rationale": "Missing runbooks increase MTTR during incidents",
                "effort": "medium",
            },
            {
                "priority": "high",
                "action": "Implement mandatory capacity reviews before integrations",
                "rationale": "3 incidents caused by insufficient capacity planning",
                "effort": "low",
            },
            {
                "priority": "medium",
                "action": "Add circuit breakers to all tier-1 service dependencies",
                "rationale": "Cascading failures amplify impact significantly",
                "effort": "high",
            },
            {
                "priority": "medium",
                "action": "Establish quarterly resource limit reviews",
                "rationale": "Multiple incidents caused by outdated resource limits",
                "effort": "low",
            },
        ],
    }
