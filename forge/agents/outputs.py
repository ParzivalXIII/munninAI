"""
Pydantic Models for Agent Structured Outputs

Defines the schemas that Cognee's LLM will use for structured extraction.
This replaces response_model=str with proper typed schemas.
"""

from pydantic import BaseModel, Field


class DiagnosisResult(BaseModel):
    """Structured diagnosis from the Incident Responder agent."""

    root_cause_suggestion: str = Field(
        ..., min_length=10, description="Most likely root cause based on similar incidents"
    )
    resolution_steps: list[str] = Field(
        default_factory=list, description="Specific steps to resolve the incident"
    )
    diagnosis_summary: str = Field(
        ..., min_length=10, description="Brief summary of the situation"
    )
    confidence: float = Field(
        default=0.7, ge=0.0, le=1.0, description="Confidence score for the diagnosis"
    )
    similar_incident_references: list[str] = Field(
        default_factory=list, description="References to similar historical incidents"
    )


class InvestigationUpdate(BaseModel):
    """Updated diagnosis when continuing an incident investigation."""

    updated_diagnosis: str = Field(..., min_length=10)
    next_steps: list[str] = Field(default_factory=list)
    confidence_change: float = Field(default=0.0, description="How confidence changed (±)")


class PostmortemOutput(BaseModel):
    """Structured postmortem report from the Postmortem Generator."""

    summary: str = Field(..., min_length=10, description="2-3 sentence overview")
    direct_cause: str = Field(..., min_length=10, description="Immediate technical cause")
    contributing_factors: list[str] = Field(default_factory=list)
    why_it_happened: str = Field(..., min_length=10, description="Deeper systemic explanation")
    users_affected: int = Field(default=0, ge=0)
    revenue_impact_usd: float = Field(default=0.0, ge=0.0)
    duration_minutes: int = Field(default=0, ge=0)
    immediate_action: str = Field(..., min_length=5)
    long_term_fix: str = Field(default="")
    action_items: list[str] = Field(default_factory=list)
    lessons_learned: list[str] = Field(default_factory=list)
    preventive_measures: list[str] = Field(default_factory=list)


class RecommendationItem(BaseModel):
    """A single recommendation."""

    priority: str = Field(default="medium", pattern="^(high|medium|low)$")
    action: str = Field(..., min_length=5)
    rationale: str = Field(default="")
    effort: str = Field(default="medium", pattern="^(low|medium|high)$")


class RecommendationsOutput(BaseModel):
    """Prioritized recommendations from the Knowledge Gap Detector."""

    recommendations: list[RecommendationItem] = Field(default_factory=list)
    summary: str = Field(default="", description="Overall summary of findings")
