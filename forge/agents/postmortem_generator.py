"""
Postmortem Generator Agent

Auto-generates structured postmortem reports from incident session memory.
"""

from datetime import datetime, timezone
from typing import Any

import structlog
from cognee import SearchType

from forge.agents.base import BaseAgent
from forge.agents.outputs import PostmortemOutput
from forge.core.cognee_client import CogneeClient
from forge.core.exceptions import AgentError

logger = structlog.get_logger(__name__)


class PostmortemGenerator(BaseAgent):
    """
    Postmortem Generator Agent - Auto-generates postmortem reports.

    Features:
    - Pulls context from incident session memory
    - Queries knowledge graph for related incidents and architecture
    - Generates structured postmortem with root cause analysis
    - Stores postmortem back into Cognee for future recall
    - Identifies action items and preventive measures
    """

    def __init__(
        self,
        cognee_client: CogneeClient | None = None,
    ) -> None:
        """Initialize Postmortem Generator agent."""
        super().__init__(name="postmortem_generator", cognee_client=cognee_client)

    async def generate_postmortem(
        self,
        incident_id: str,
        incident_session_id: str,
        additional_context: str = "",
    ) -> dict[str, Any]:
        """
        Generate a structured postmortem from incident session memory.

        Args:
            incident_id: The incident ID (e.g., INC-016)
            incident_session_id: Session ID from the incident response
            additional_context: Any extra context to include

        Returns:
            Structured postmortem report
        """
        await self.ensure_connected()

        self.logger.info(
            "Generating postmortem",
            incident_id=incident_id,
            session_id=incident_session_id,
        )

        try:
            # Step 1: Retrieve session memory from the incident
            session_context = await self._retrieve_session_context(incident_session_id)

            # Step 2: Query for similar past incidents for comparison
            similar_incidents = await self._find_similar_incidents(incident_id)

            # Step 3: Query architecture for affected service details
            architecture_context = await self._get_architecture_context()

            # Step 4: Query existing postmortems for format reference
            postmortem_examples = await self._get_postmortem_examples()

            # Step 5: Generate the postmortem using LLM
            postmortem = await self._generate_postmortem_content(
                incident_id=incident_id,
                session_context=session_context,
                similar_incidents=similar_incidents,
                architecture_context=architecture_context,
                postmortem_examples=postmortem_examples,
                additional_context=additional_context,
            )

            # Step 6: Store the postmortem in Cognee
            await self._store_postmortem(incident_id, postmortem)

            self.logger.info("Postmortem generated and stored", incident_id=incident_id)

            return postmortem

        except Exception as e:
            self.logger.error("Failed to generate postmortem", error=str(e))
            raise AgentError(
                f"Failed to generate postmortem: {e}",
                agent_name=self.name,
            ) from e

    async def _retrieve_session_context(self, session_id: str) -> str:
        """Retrieve session memory from the incident response."""
        try:
            from cognee.infrastructure.session.get_session_manager import get_session_manager
            from cognee.modules.users.methods import get_default_user

            user = await get_default_user()
            sm = get_session_manager()

            history = await sm.get_session(
                user_id=str(user.id),
                session_id=session_id,
                formatted=True,
                include_context=True,
            )

            return history if history else "No session history available."

        except Exception as e:
            self.logger.warning("Failed to retrieve session context", error=str(e))
            return "Session context unavailable."

    async def _find_similar_incidents(self, incident_id: str) -> str:
        """Find similar past incidents for comparison."""
        try:
            results = await self.cognee.recall(
                query_text=f"Incident {incident_id} root cause and resolution",
                datasets=[self.settings.incidents_dataset],
                search_type=SearchType.GRAPH_COMPLETION,
                top_k=3,
            )

            parts = []
            for result in results:
                text = self._extract_text(result)
                parts.append(text[:400])

            return "\n\n---\n\n".join(parts) if parts else "No similar incidents found."

        except Exception as e:
            self.logger.warning("Failed to find similar incidents", error=str(e))
            return "Similar incident lookup failed."

    async def _get_architecture_context(self) -> str:
        """Get architecture details for affected services."""
        try:
            results = await self.cognee.recall(
                query_text="Service dependencies, team ownership, and runbooks",
                datasets=[self.settings.architecture_dataset],
                search_type=SearchType.GRAPH_COMPLETION,
                top_k=3,
            )

            parts = []
            for result in results:
                text = self._extract_text(result)
                parts.append(text[:300])

            return "\n\n".join(parts) if parts else "Architecture context unavailable."

        except Exception as e:
            self.logger.warning("Failed to get architecture context", error=str(e))
            return "Architecture context unavailable."

    async def _get_postmortem_examples(self) -> str:
        """Get existing postmortems as format reference."""
        try:
            results = await self.cognee.recall(
                query_text="Postmortem with root cause analysis, action items, and lessons learned",
                datasets=[self.settings.postmortems_dataset],
                search_type=SearchType.GRAPH_COMPLETION,
                top_k=2,
            )

            parts = []
            for result in results:
                text = self._extract_text(result)
                parts.append(text[:500])

            return "\n\n---\n\n".join(parts) if parts else "No example postmortems found."

        except Exception as e:
            self.logger.warning("Failed to get postmortem examples", error=str(e))
            return ""

    async def _generate_postmortem_content(
        self,
        incident_id: str,
        session_context: str,
        similar_incidents: str,
        architecture_context: str,
        postmortem_examples: str,
        additional_context: str,
    ) -> dict[str, Any]:
        """Generate postmortem content using LLM."""
        from cognee.infrastructure.llm.LLMGateway import LLMGateway

        # Build comprehensive context
        context_parts = [
            f"INCIDENT ID: {incident_id}",
            f"TIMESTAMP: {datetime.now(timezone.utc).isoformat()}",
            "",
            "=== INCIDENT SESSION MEMORY ===",
            session_context,
            "",
            "=== SIMILAR HISTORICAL INCIDENTS ===",
            similar_incidents,
            "",
            "=== SERVICE ARCHITECTURE ===",
            architecture_context,
        ]

        if postmortem_examples:
            context_parts.extend([
                "",
                "=== EXAMPLE POSTMORTEM FORMAT ===",
                postmortem_examples,
            ])

        if additional_context:
            context_parts.extend([
                "",
                "=== ADDITIONAL CONTEXT ===",
                additional_context,
            ])

        full_context = "\n".join(context_parts)

        system_prompt = """You are an expert DevOps postmortem author. Generate a comprehensive, structured postmortem report based on the incident context provided.

The postmortem MUST include these sections:

1. SUMMARY: 2-3 sentence overview of what happened
2. ROOT CAUSE ANALYSIS:
   - Direct Cause: The immediate technical cause
   - Contributing Factors: List of factors that made the incident worse
   - Why It Happened: Deeper explanation of systemic issues
3. IMPACT ASSESSMENT: Users affected, revenue impact, duration
4. RESOLUTION:
   - Immediate Action: What was done to resolve the incident
   - Long-Term Fix: What should be done to prevent recurrence
5. ACTION ITEMS: Specific tasks with owners and status (use format: [STATUS] Description - Owner: name)
6. LESSONS LEARNED: Key takeaways (bullet points)
7. PREVENTIVE MEASURES: Concrete steps to prevent similar incidents

Be specific, technical, and actionable. Reference similar incidents when relevant.
If information is not available, state "Unknown" rather than making things up."""

        postmortem_result = await LLMGateway.acreate_structured_output(
            text_input=full_context,
            system_prompt=system_prompt,
            response_model=PostmortemOutput,
        )

        # Format the postmortem text from structured output
        factors = "\n".join(f"  - {f}" for f in postmortem_result.contributing_factors) if postmortem_result.contributing_factors else "  - None identified"
        items = "\n".join(f"  • {item}" for item in postmortem_result.action_items) if postmortem_result.action_items else "  • None specified"
        lessons = "\n".join(f"  • {lesson}" for lesson in postmortem_result.lessons_learned) if postmortem_result.lessons_learned else "  • None specified"
        measures = "\n".join(f"  • {measure}" for measure in postmortem_result.preventive_measures) if postmortem_result.preventive_measures else "  • None specified"

        postmortem_text = f"""SUMMARY: {postmortem_result.summary}

ROOT CAUSE ANALYSIS:
  Direct Cause: {postmortem_result.direct_cause}

  Contributing Factors:
{factors}

  Why It Happened: {postmortem_result.why_it_happened}

IMPACT ASSESSMENT:
  Users Affected: {postmortem_result.users_affected}
  Revenue Impact: ${postmortem_result.revenue_impact_usd:,.0f}
  Duration: {postmortem_result.duration_minutes} minutes

RESOLUTION:
  Immediate Action: {postmortem_result.immediate_action}
  Long-Term Fix: {postmortem_result.long_term_fix}

ACTION ITEMS:
{items}

LESSONS LEARNED:
{lessons}

PREVENTIVE MEASURES:
{measures}"""

        return {
            "incident_id": incident_id,
            "postmortem_text": postmortem_text,
            "session_context": session_context,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _store_postmortem(self, incident_id: str, postmortem: dict[str, Any]) -> None:
        """Store the generated postmortem in Cognee."""
        try:
            await self.cognee.remember(
                data=postmortem["postmortem_text"],
                dataset_name=self.settings.postmortems_dataset,
                temporal_cognify=True,
                node_set=["postmortems", "devops"],
                self_improvement=False,
            )
            self.logger.info("Postmortem stored in knowledge graph", incident_id=incident_id)
        except Exception as e:
            self.logger.warning("Failed to store postmortem", error=str(e))

    @staticmethod
    def _extract_text(result: Any) -> str:
        """Extract text from various result formats."""
        if isinstance(result, dict):
            return result.get("text", str(result))
        elif hasattr(result, "text"):
            return result.text
        return str(result)
