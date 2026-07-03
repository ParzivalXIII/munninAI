"""
Pydantic Data Models for DevOps Datasets

Type-safe schemas for incidents, architecture, and postmortems.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


# =============================================================================
# Incident Models
# =============================================================================


class IncidentTimelineEvent(BaseModel):
    """Single event in an incident timeline."""

    timestamp: datetime
    event: str = Field(..., description="Description of what happened")


class IncidentImpact(BaseModel):
    """Impact assessment for an incident."""

    users_affected: int = Field(default=0, ge=0)
    revenue_impact_usd: float = Field(default=0.0, ge=0.0)
    failed_transactions: int = Field(default=0, ge=0)


class Incident(BaseModel):
    """DevOps incident report."""

    id: str = Field(..., description="Incident ID (e.g., INC-001)")
    title: str = Field(..., min_length=5, max_length=500)
    timestamp: datetime
    severity: Literal["P1", "P2", "P3", "P4"]
    status: Literal["open", "investigating", "monitoring", "resolved"]
    affected_services: list[str] = Field(default_factory=list)
    symptoms: list[str] = Field(default_factory=list)
    root_cause: str = Field(..., min_length=10)
    resolution: str = Field(..., min_length=10)
    timeline: list[IncidentTimelineEvent] = Field(default_factory=list)
    duration_minutes: int = Field(default=0, ge=0)
    impact: IncidentImpact = Field(default_factory=IncidentImpact)
    on_call_engineer: str = Field(default="Unknown")
    tags: list[str] = Field(default_factory=list)
    postmortem_id: str | None = Field(default=None)

    @field_validator("id")
    @classmethod
    def validate_incident_id(cls, v: str) -> str:
        """Ensure incident ID follows INC-XXX format."""
        if not v.startswith("INC-"):
            raise ValueError("Incident ID must start with 'INC-'")
        return v


class IncidentDataset(BaseModel):
    """Collection of incidents with metadata."""

    metadata: dict[str, Any] = Field(default_factory=dict)
    incidents: list[Incident] = Field(default_factory=list)


# =============================================================================
# Architecture Models
# =============================================================================


class Service(BaseModel):
    """Microservice definition."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=10)
    team: str = Field(..., min_length=1)
    language: str = Field(default="Python")
    framework: str = Field(default="FastAPI")
    database: str | None = Field(default=None)
    cache: str | None = Field(default=None)
    dependencies: list[str] = Field(default_factory=list)
    external_apis: list[str] = Field(default_factory=list)
    message_queue: str | None = Field(default=None)
    health_check: str = Field(default="/health")
    port: int = Field(default=8080, ge=1, le=65535)
    replicas: int = Field(default=1, ge=1)
    cpu_limit: str = Field(default="500m")
    memory_limit: str = Field(default="512Mi")
    runbook: str = Field(default="")
    criticality: Literal["tier-1", "tier-2", "tier-3"] = Field(default="tier-2")
    sla: str = Field(default="99.9%")


class Team(BaseModel):
    """Engineering team definition."""

    name: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1)
    description: str = Field(default="")
    lead: str = Field(default="Unknown")
    members: list[str] = Field(default_factory=list)
    services: list[str] = Field(default_factory=list)
    on_call_rotation: str = Field(default="")
    slack_channel: str = Field(default="")
    pagerduty_service: str = Field(default="")


class RunbookSection(BaseModel):
    """Section within a runbook."""

    title: str = Field(..., min_length=1)
    content: str = Field(..., min_length=10)


class Runbook(BaseModel):
    """Operational runbook for a service."""

    id: str = Field(..., min_length=1)
    service: str = Field(..., min_length=1)
    title: str = Field(..., min_length=5)
    sections: list[RunbookSection] = Field(default_factory=list)


class Infrastructure(BaseModel):
    """Infrastructure configuration."""

    kubernetes_cluster: str = Field(default="")
    cloud_provider: str = Field(default="AWS")
    region: str = Field(default="us-east-1")
    databases: dict[str, Any] = Field(default_factory=dict)
    monitoring: dict[str, Any] = Field(default_factory=dict)
    ci_cd: dict[str, Any] = Field(default_factory=dict)


class ArchitectureDataset(BaseModel):
    """Complete architecture definition."""

    metadata: dict[str, Any] = Field(default_factory=dict)
    services: list[Service] = Field(default_factory=list)
    teams: list[Team] = Field(default_factory=list)
    runbooks: list[Runbook] = Field(default_factory=list)
    infrastructure: Infrastructure = Field(default_factory=Infrastructure)


# =============================================================================
# Postmortem Models
# =============================================================================


class RootCauseAnalysis(BaseModel):
    """Root cause analysis for a postmortem."""

    direct_cause: str = Field(..., min_length=10)
    contributing_factors: list[str] = Field(default_factory=list)
    why_it_happened: str = Field(default="", min_length=0)


class ImpactAssessment(BaseModel):
    """Impact assessment for a postmortem."""

    duration_minutes: int = Field(default=0, ge=0)
    users_affected: int = Field(default=0, ge=0)
    revenue_impact_usd: float = Field(default=0.0, ge=0.0)
    failed_transactions: int = Field(default=0, ge=0)
    customer_complaints: int = Field(default=0, ge=0)
    data_loss: bool = Field(default=False)


class Resolution(BaseModel):
    """Resolution details for a postmortem."""

    immediate_action: str = Field(..., min_length=10)
    long_term_fix: str = Field(default="", min_length=0)


class ActionItem(BaseModel):
    """Action item from a postmortem."""

    id: str = Field(..., min_length=1)
    description: str = Field(..., min_length=10)
    owner: str = Field(default="Unassigned")
    status: Literal["pending", "in_progress", "completed", "cancelled"] = Field(
        default="pending"
    )
    completed_date: datetime | None = Field(default=None)
    target_date: datetime | None = Field(default=None)


class Postmortem(BaseModel):
    """Post-incident postmortem report."""

    id: str = Field(..., min_length=1)
    incident_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=10)
    date: str = Field(..., min_length=1)
    author: str = Field(default="Unknown")
    severity: Literal["P1", "P2", "P3", "P4"]
    summary: str = Field(..., min_length=20)
    root_cause_analysis: RootCauseAnalysis
    impact_assessment: ImpactAssessment = Field(default_factory=ImpactAssessment)
    resolution: Resolution
    action_items: list[ActionItem] = Field(default_factory=list)
    lessons_learned: list[str] = Field(default_factory=list)
    preventive_measures: list[str] = Field(default_factory=list)
    follow_up_notes: str = Field(default="", min_length=0)

    @field_validator("incident_id")
    @classmethod
    def validate_incident_id(cls, v: str) -> str:
        """Ensure incident ID follows INC-XXX format."""
        if not v.startswith("INC-"):
            raise ValueError("Incident ID must start with 'INC-'")
        return v


class PostmortemDataset(BaseModel):
    """Collection of postmortems with metadata."""

    metadata: dict[str, Any] = Field(default_factory=dict)
    postmortems: list[Postmortem] = Field(default_factory=list)
