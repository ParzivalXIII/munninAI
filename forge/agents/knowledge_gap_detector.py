"""
Knowledge Gap Detector Agent

Analyzes the knowledge graph to identify missing documentation,
undetected patterns, and areas needing attention.
"""

import re
from datetime import datetime, timezone
from typing import Any

import structlog
from cognee import SearchType

from forge.agents.base import BaseAgent
from forge.agents.outputs import RecommendationsOutput
from forge.core.cognee_client import CogneeClient
from forge.core.exceptions import AgentError

logger = structlog.get_logger(__name__)

# Precompiled regex patterns
_INCIDENT_ID_REGEX = re.compile(r"INC-\d+")
_SERVICE_REGEX = re.compile(r"Service:\s*(\S+)")


class KnowledgeGapDetector(BaseAgent):
    """
    Knowledge Gap Detector Agent - Identifies missing knowledge.

    Features:
    - Analyzes incidents to find recurring patterns without postmortems
    - Identifies services with incidents but no runbooks
    - Detects missing documentation for common issues
    - Suggests areas for knowledge base improvement
    - Uses truth subspace reranking to prioritize gaps
    """

    def __init__(
        self,
        cognee_client: CogneeClient | None = None,
    ) -> None:
        """Initialize Knowledge Gap Detector agent."""
        super().__init__(name="knowledge_gap_detector", cognee_client=cognee_client)

    async def detect_gaps(self) -> dict[str, Any]:
        """
        Detect knowledge gaps across all datasets.

        Returns:
            Dictionary with detected gaps categorized by type:
            - missing_postmortems: Incidents without postmortems
            - missing_runbooks: Services without runbooks
            - recurring_patterns: Patterns that appear multiple times
            - documentation_gaps: Areas needing better documentation
            - recommendations: Prioritized list of improvements
        """
        await self.ensure_connected()

        self.logger.info("Starting knowledge gap detection")

        try:
            # Step 1: Find incidents without postmortems
            missing_postmortems = await self._find_incidents_without_postmortems()

            # Step 2: Find services without runbooks
            missing_runbooks = await self._find_services_without_runbooks()

            # Step 3: Identify recurring incident patterns
            recurring_patterns = await self._find_recurring_patterns()

            # Step 4: Detect documentation gaps
            documentation_gaps = await self._detect_documentation_gaps()

            # Step 5: Generate prioritized recommendations
            recommendations = await self._generate_recommendations(
                missing_postmortems=missing_postmortems,
                missing_runbooks=missing_runbooks,
                recurring_patterns=recurring_patterns,
                documentation_gaps=documentation_gaps,
            )

            gaps_report = {
                "missing_postmortems": missing_postmortems,
                "missing_runbooks": missing_runbooks,
                "recurring_patterns": recurring_patterns,
                "documentation_gaps": documentation_gaps,
                "recommendations": recommendations,
                "detected_at": datetime.now(timezone.utc).isoformat(),
            }

            self.logger.info(
                "Knowledge gap detection complete",
                missing_postmortems_count=len(missing_postmortems),
                missing_runbooks_count=len(missing_runbooks),
                recurring_patterns_count=len(recurring_patterns),
            )

            return gaps_report

        except Exception as e:
            self.logger.error("Failed to detect knowledge gaps", error=str(e))
            raise AgentError(
                f"Failed to detect knowledge gaps: {e}",
                agent_name=self.name,
            ) from e

    async def _find_incidents_without_postmortems(self) -> list[dict[str, Any]]:
        """Find incidents that don't have corresponding postmortems."""
        try:
            # Query for all incidents
            incidents_result = await self.cognee.recall(
                query_text="All incidents with their IDs and postmortem references",
                datasets=[self.settings.incidents_dataset],
                search_type=SearchType.GRAPH_COMPLETION,
                top_k=20,
            )

            # Query for all postmortems
            postmortems_result = await self.cognee.recall(
                query_text="All postmortems with their incident IDs",
                datasets=[self.settings.postmortems_dataset],
                search_type=SearchType.GRAPH_COMPLETION,
                top_k=20,
            )

            # Parse and compare
            incidents = self._parse_incident_ids(incidents_result)
            postmortem_incident_ids = self._parse_postmortem_incident_ids(postmortems_result)

            # Find incidents without postmortems
            missing = []
            for incident in incidents:
                if incident["id"] not in postmortem_incident_ids:
                    missing.append(incident)

            return missing

        except Exception as e:
            self.logger.warning("Failed to find incidents without postmortems", error=str(e))
            return []

    async def _find_services_without_runbooks(self) -> list[dict[str, Any]]:
        """Find services that don't have runbooks."""
        try:
            # Query for all services
            services_result = await self.cognee.recall(
                query_text="All services with their names and runbook references",
                datasets=[self.settings.architecture_dataset],
                search_type=SearchType.GRAPH_COMPLETION,
                top_k=20,
            )

            # Query for all runbooks
            runbooks_result = await self.cognee.recall(
                query_text="All runbooks with their service names",
                datasets=[self.settings.architecture_dataset],
                search_type=SearchType.GRAPH_COMPLETION,
                top_k=20,
            )

            # Parse and compare
            services = self._parse_service_names(services_result)
            runbook_services = self._parse_runbook_services(runbooks_result)

            # Find services without runbooks
            missing = []
            for service in services:
                if service["name"] not in runbook_services:
                    missing.append(service)

            return missing

        except Exception as e:
            self.logger.warning("Failed to find services without runbooks", error=str(e))
            return []

    async def _find_recurring_patterns(self) -> list[dict[str, Any]]:
        """Find incident patterns that occur multiple times."""
        try:
            # Query for incident patterns and tags
            patterns_result = await self.cognee.recall(
                query_text="Incident patterns, recurring issues, and common tags across multiple incidents",
                datasets=[self.settings.incidents_dataset],
                search_type=SearchType.GRAPH_COMPLETION,
                top_k=10,
            )

            # Also check postmortems for recurring lessons
            lessons_result = await self.cognee.recall(
                query_text="Recurring lessons learned and preventive measures from postmortems",
                datasets=[self.settings.postmortems_dataset],
                search_type=SearchType.GRAPH_COMPLETION,
                top_k=10,
            )

            patterns = []
            for result in patterns_result:
                text = self._extract_text(result)
                patterns.append({
                    "pattern": text[:300],
                    "source": "incidents",
                })

            for result in lessons_result:
                text = self._extract_text(result)
                patterns.append({
                    "pattern": text[:300],
                    "source": "postmortems",
                })

            return patterns

        except Exception as e:
            self.logger.warning("Failed to find recurring patterns", error=str(e))
            return []

    async def _detect_documentation_gaps(self) -> list[dict[str, Any]]:
        """Detect areas where documentation is insufficient."""
        try:
            # Query for areas with limited knowledge
            gaps_result = await self.cognee.recall(
                query_text="Areas with limited documentation, missing troubleshooting guides, or insufficient runbook coverage",
                datasets=self.get_all_datasets(),
                search_type=SearchType.GRAPH_COMPLETION,
                top_k=10,
            )

            gaps = []
            for result in gaps_result:
                text = self._extract_text(result)
                gaps.append({
                    "gap": text[:300],
                    "severity": "medium",  # Could be enhanced with LLM analysis
                })

            return gaps

        except Exception as e:
            self.logger.warning("Failed to detect documentation gaps", error=str(e))
            return []

    async def _generate_recommendations(
        self,
        missing_postmortems: list[dict[str, Any]],
        missing_runbooks: list[dict[str, Any]],
        recurring_patterns: list[dict[str, Any]],
        documentation_gaps: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Generate prioritized recommendations based on detected gaps."""
        from cognee.infrastructure.llm.LLMGateway import LLMGateway

        # Build context for LLM
        context_parts = [
            "=== KNOWLEDGE GAPS DETECTED ===",
            "",
        ]

        if missing_postmortems:
            context_parts.append(f"INCIDENTS WITHOUT POSTMORTEM ({len(missing_postmortems)}):")
            for incident in missing_postmortems[:5]:
                context_parts.append(f"  - {incident.get('id')}: {incident.get('title', 'Unknown')}")
            context_parts.append("")

        if missing_runbooks:
            context_parts.append(f"SERVICES WITHOUT RUNBOOKS ({len(missing_runbooks)}):")
            for service in missing_runbooks[:5]:
                context_parts.append(f"  - {service.get('name')}: {service.get('description', 'Unknown')}")
            context_parts.append("")

        if recurring_patterns:
            context_parts.append(f"RECURRING PATTERNS ({len(recurring_patterns)}):")
            for pattern in recurring_patterns[:5]:
                context_parts.append(f"  - {pattern['pattern'][:200]}")
            context_parts.append("")

        if documentation_gaps:
            context_parts.append(f"DOCUMENTATION GAPS ({len(documentation_gaps)}):")
            for gap in documentation_gaps[:5]:
                context_parts.append(f"  - {gap['gap'][:200]}")
            context_parts.append("")

        full_context = "\n".join(context_parts)

        system_prompt = """You are a DevOps knowledge management expert. Based on the detected knowledge gaps, generate a prioritized list of recommendations.

For each recommendation, provide:
1. PRIORITY: high, medium, or low
2. ACTION: Specific action to take
3. RATIONALE: Why this is important
4. EFFORT: Estimated effort (low, medium, high)

Focus on actions that will have the most impact on incident response time and prevention.
Return recommendations in priority order (highest first)."""

        try:
            recs_output = await LLMGateway.acreate_structured_output(
                text_input=full_context,
                system_prompt=system_prompt,
                response_model=RecommendationsOutput,
            )

            # Convert to dict format
            recommendations = []
            for rec in recs_output.recommendations[:10]:
                recommendations.append({
                    "recommendation": f"[{rec.priority.upper()}] {rec.action} — {rec.rationale} (Effort: {rec.effort})",
                    "priority": rec.priority,
                })

            return recommendations

        except Exception as e:
            self.logger.warning("Failed to generate recommendations", error=str(e))
            # Fallback to simple recommendations
            return [
                {"recommendation": f"Create postmortems for {len(missing_postmortems)} incidents without them"},
                {"recommendation": f"Write runbooks for {len(missing_runbooks)} services without documentation"},
                {"recommendation": "Address recurring patterns with preventive measures"},
            ]

    def _parse_incident_ids(self, results: list[Any]) -> list[dict[str, Any]]:
        """Parse incident IDs from recall results."""
        incidents = []
        for result in results:
            text = self._extract_text(result)
            matches = _INCIDENT_ID_REGEX.findall(text)
            for match in matches:
                incidents.append({"id": match, "title": text[:200]})
        return incidents

    def _parse_postmortem_incident_ids(self, results: list[Any]) -> set[str]:
        """Parse incident IDs referenced in postmortems."""
        incident_ids = set()
        for result in results:
            text = self._extract_text(result)
            matches = _INCIDENT_ID_REGEX.findall(text)
            incident_ids.update(matches)
        return incident_ids

    def _parse_service_names(self, results: list[Any]) -> list[dict[str, Any]]:
        """Parse service names from recall results."""
        services = []
        for result in results:
            text = self._extract_text(result)
            # Look for service names (simple heuristic)
            if "SERVICE:" in text or "service" in text.lower():
                services.append({"name": text[:100], "description": text[:200]})
        return services

    def _parse_runbook_services(self, results: list[Any]) -> set[str]:
        """Parse service names that have runbooks."""
        services = set()
        for result in results:
            text = self._extract_text(result)
            if "RUNBOOK:" in text or "runbook" in text.lower():
                match = _SERVICE_REGEX.search(text)
                if match:
                    services.add(match.group(1))
        return services

    @staticmethod
    def _extract_text(result: Any) -> str:
        """Extract text from various result formats."""
        if isinstance(result, dict):
            return result.get("text", str(result))
        elif hasattr(result, "text"):
            return result.text
        return str(result)
