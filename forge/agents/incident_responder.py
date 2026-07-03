"""
Incident Responder Agent

Real-time incident diagnosis with temporal awareness and session memory.
"""

import re
from datetime import datetime
from typing import Any

import structlog
from cognee import SearchType

from forge.agents.base import BaseAgent
from forge.agents.outputs import DiagnosisResult, InvestigationUpdate
from forge.core.cognee_client import CogneeClient
from forge.core.exceptions import AgentError, RecallError

logger = structlog.get_logger(__name__)

# Precompiled regex for confidence score extraction
_CONFIDENCE_REGEX = re.compile(r"confidence[:\s]+(\d+\.?\d*)")


class IncidentResponder(BaseAgent):
    """
    Incident Responder Agent - Real-time incident diagnosis.

    Features:
    - Queries knowledge graph for similar historical incidents
    - Uses temporal awareness to reconstruct incident timelines
    - Maintains session context across the incident lifecycle
    - Provides diagnosis and resolution suggestions
    - Bridges session learnings into permanent memory after resolution
    """

    def __init__(
        self,
        cognee_client: CogneeClient | None = None,
        session_id: str | None = None,
    ) -> None:
        """
        Initialize Incident Responder agent.

        Args:
            cognee_client: Optional Cognee client instance
            session_id: Optional session ID (generated if not provided)
        """
        super().__init__(name="incident_responder", cognee_client=cognee_client)
        self.session_id = session_id or self.generate_session_id("incident")
        self.logger = logger.bind(session_id=self.session_id)

    async def diagnose_incident(
        self,
        alert_text: str,
        affected_services: list[str] | None = None,
        severity: str = "P2",
    ) -> dict[str, Any]:
        """
        Diagnose an incident using knowledge graph and temporal awareness.

        Args:
            alert_text: Description of the incident/alert
            affected_services: List of affected service names
            severity: Incident severity (P1, P2, P3, P4)

        Returns:
            Dictionary with diagnosis results including:
            - similar_incidents: List of similar historical incidents
            - timeline: Reconstructed incident timeline
            - root_cause_suggestion: Suggested root cause
            - resolution_suggestion: Suggested resolution steps
            - confidence: Confidence score (0.0-1.0)
        """
        await self.ensure_connected()

        self.logger.info(
            "Starting incident diagnosis",
            alert_preview=alert_text[:100],
            affected_services=affected_services,
            severity=severity,
        )

        try:
            # Step 1: Query for similar incidents using graph completion
            similar_incidents = await self._find_similar_incidents(alert_text, affected_services)

            # Step 2: Query for temporal patterns if we have timestamps
            temporal_context = await self._get_temporal_context(alert_text)

            # Step 3: Query architecture for service dependencies
            service_context = await self._get_service_context(affected_services or [])

            # Step 4: Synthesize diagnosis
            diagnosis = await self._synthesize_diagnosis(
                alert_text=alert_text,
                similar_incidents=similar_incidents,
                temporal_context=temporal_context,
                service_context=service_context,
                severity=severity,
            )

            self.logger.info(
                "Incident diagnosis complete",
                similar_incidents_count=len(similar_incidents),
                confidence=diagnosis.get("confidence", 0.0),
            )

            return diagnosis

        except Exception as e:
            self.logger.error("Failed to diagnose incident", error=str(e))
            raise AgentError(
                f"Failed to diagnose incident: {e}",
                agent_name=self.name,
            ) from e

    async def _find_similar_incidents(
        self,
        alert_text: str,
        affected_services: list[str] | None,
    ) -> list[dict[str, Any]]:
        """Find similar historical incidents from knowledge graph."""
        try:
            # Build query with service context
            query = alert_text
            if affected_services:
                services_str = ", ".join(affected_services)
                query = f"Incident affecting {services_str}: {alert_text}"

            # Query incidents dataset with graph completion
            results = await self.cognee.recall(
                query_text=query,
                datasets=[self.settings.incidents_dataset],
                search_type=SearchType.GRAPH_COMPLETION,
                top_k=5,
                session_id=self.session_id,
            )

            # Parse results into structured format
            similar_incidents = []
            for result in results:
                if isinstance(result, dict):
                    similar_incidents.append(result)
                elif hasattr(result, "text"):
                    similar_incidents.append({"text": result.text, "score": getattr(result, "score", 0.0)})
                else:
                    similar_incidents.append({"text": str(result), "score": 0.0})

            return similar_incidents

        except Exception as e:
            self.logger.warning("Failed to find similar incidents", error=str(e))
            return []

    async def _get_temporal_context(self, alert_text: str) -> list[dict[str, Any]]:
        """Get temporal context using temporal search."""
        try:
            # Use temporal search to find incidents in similar timeframes
            results = await self.cognee.recall(
                query_text=alert_text,
                datasets=[self.settings.incidents_dataset],
                search_type=SearchType.TEMPORAL,
                top_k=3,
                session_id=self.session_id,
            )

            temporal_context = []
            for result in results:
                if isinstance(result, dict):
                    temporal_context.append(result)
                elif hasattr(result, "text"):
                    temporal_context.append({"text": result.text})
                else:
                    temporal_context.append({"text": str(result)})

            return temporal_context

        except Exception as e:
            self.logger.warning("Failed to get temporal context", error=str(e))
            return []

    async def _get_service_context(self, affected_services: list[str]) -> list[dict[str, Any]]:
        """Get service architecture context."""
        if not affected_services:
            return []

        try:
            # Query architecture dataset for service information
            services_str = ", ".join(affected_services)
            query = f"Service information for {services_str} including dependencies, team ownership, and runbooks"

            results = await self.cognee.recall(
                query_text=query,
                datasets=[self.settings.architecture_dataset],
                search_type=SearchType.GRAPH_COMPLETION,
                top_k=3,
                session_id=self.session_id,
            )

            service_context = []
            for result in results:
                if isinstance(result, dict):
                    service_context.append(result)
                elif hasattr(result, "text"):
                    service_context.append({"text": result.text})
                else:
                    service_context.append({"text": str(result)})

            return service_context

        except Exception as e:
            self.logger.warning("Failed to get service context", error=str(e))
            return []

    async def _synthesize_diagnosis(
        self,
        alert_text: str,
        similar_incidents: list[dict[str, Any]],
        temporal_context: list[dict[str, Any]],
        service_context: list[dict[str, Any]],
        severity: str,
    ) -> dict[str, Any]:
        """Synthesize all context into a diagnosis."""
        # Build comprehensive context for LLM
        context_parts = [
            f"ALERT: {alert_text}",
            f"SEVERITY: {severity}",
            "",
        ]

        if similar_incidents:
            context_parts.append("SIMILAR HISTORICAL INCIDENTS:")
            for i, incident in enumerate(similar_incidents[:3], 1):
                text = incident.get("text", str(incident))
                context_parts.append(f"{i}. {text[:500]}")
            context_parts.append("")

        if temporal_context:
            context_parts.append("TEMPORAL CONTEXT:")
            for ctx in temporal_context[:2]:
                text = ctx.get("text", str(ctx))
                context_parts.append(f"- {text[:300]}")
            context_parts.append("")

        if service_context:
            context_parts.append("SERVICE ARCHITECTURE:")
            for ctx in service_context[:2]:
                text = ctx.get("text", str(ctx))
                context_parts.append(f"- {text[:300]}")
            context_parts.append("")

        full_context = "\n".join(context_parts)

        # Use LLM to synthesize diagnosis
        try:
            from cognee.infrastructure.llm.LLMGateway import LLMGateway

            system_prompt = """You are an expert DevOps incident responder. Analyze the alert and context to provide:

1. ROOT CAUSE SUGGESTION: What is the most likely root cause based on similar incidents?
2. RESOLUTION STEPS: What specific steps should be taken to resolve this incident?
3. DIAGNOSIS SUMMARY: Brief summary of the situation and recommended actions.
4. CONFIDENCE: Rate your confidence (0.0-1.0) in this diagnosis.

Be specific and actionable. Reference similar incidents when relevant."""

            diagnosis_result = await LLMGateway.acreate_structured_output(
                text_input=full_context,
                system_prompt=system_prompt,
                response_model=DiagnosisResult,
            )

            return {
                "diagnosis": diagnosis_result.diagnosis_summary,
                "root_cause": diagnosis_result.root_cause_suggestion,
                "resolution_steps": diagnosis_result.resolution_steps,
                "similar_incidents": similar_incidents,
                "temporal_context": temporal_context,
                "service_context": service_context,
                "confidence": diagnosis_result.confidence,
                "session_id": self.session_id,
            }

        except Exception as e:
            self.logger.warning("Failed to synthesize diagnosis with LLM", error=str(e))
            # Fallback to simple response
            return {
                "diagnosis": f"Based on {len(similar_incidents)} similar incidents, investigate the alert: {alert_text[:200]}",
                "similar_incidents": similar_incidents,
                "temporal_context": temporal_context,
                "service_context": service_context,
                "confidence": 0.5,
                "session_id": self.session_id,
            }

    async def continue_investigation(self, new_information: str) -> dict[str, Any]:
        """
        Continue incident investigation with new information.

        Uses session memory to maintain context across the incident.

        Args:
            new_information: New information about the incident

        Returns:
            Updated diagnosis with new context
        """
        await self.ensure_connected()

        self.logger.info("Continuing investigation", new_info_preview=new_information[:100])

        try:
            # Query with session context
            results = await self.cognee.recall(
                query_text=new_information,
                datasets=self.get_all_datasets(),
                search_type=SearchType.GRAPH_COMPLETION,
                top_k=5,
                session_id=self.session_id,  # Maintains conversation context
            )

            # Synthesize updated diagnosis
            context_parts = [f"NEW INFORMATION: {new_information}", ""]

            for i, result in enumerate(results[:3], 1):
                if isinstance(result, dict):
                    text = result.get("text", str(result))
                elif hasattr(result, "text"):
                    text = result.text
                else:
                    text = str(result)
                context_parts.append(f"{i}. {text[:500]}")

            full_context = "\n".join(context_parts)

            from cognee.infrastructure.llm.LLMGateway import LLMGateway

            system_prompt = """You are continuing to investigate an incident. Based on the new information and previous context, provide an updated diagnosis with specific next steps."""

            update = await LLMGateway.acreate_structured_output(
                text_input=full_context,
                system_prompt=system_prompt,
                response_model=InvestigationUpdate,
            )

            return {
                "updated_diagnosis": update.updated_diagnosis,
                "next_steps": update.next_steps,
                "session_id": self.session_id,
            }

        except Exception as e:
            self.logger.error("Failed to continue investigation", error=str(e))
            raise AgentError(
                f"Failed to continue investigation: {e}",
                agent_name=self.name,
            ) from e

    async def resolve_incident(self, resolution_summary: str) -> dict[str, Any]:
        """
        Mark incident as resolved and bridge session learnings into permanent memory.

        Args:
            resolution_summary: Summary of how the incident was resolved

        Returns:
            Confirmation of resolution and memory bridging
        """
        await self.ensure_connected()

        self.logger.info("Resolving incident", resolution_preview=resolution_summary[:100])

        try:
            # Bridge session memory into permanent graph
            await self.cognee.improve(
                dataset=self.settings.incidents_dataset,
                session_ids=[self.session_id],
                build_truth_subspace=True,  # Build truth subspace for future reranking
            )

            self.logger.info("Session memory bridged to permanent graph", session_id=self.session_id)

            return {
                "status": "resolved",
                "session_id": self.session_id,
                "resolution_summary": resolution_summary,
                "memory_bridged": True,
                "truth_subspace_built": True,
            }

        except Exception as e:
            self.logger.error("Failed to resolve incident", error=str(e))
            raise AgentError(
                f"Failed to resolve incident: {e}",
                agent_name=self.name,
            ) from e
