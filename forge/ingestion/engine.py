"""
Data Ingestion Engine

Transforms JSON datasets into Cognee-friendly text and ingests into knowledge graph.
"""

import json
from pathlib import Path
from typing import Any

import structlog

from forge.core.cognee_client import CogneeClient, get_cognee_client
from forge.core.config import get_settings
from forge.core.exceptions import IngestionError
from forge.ingestion.models import (
    ArchitectureDataset,
    IncidentDataset,
    PostmortemDataset,
)

logger = structlog.get_logger(__name__)


class DataFormatter:
    """Formats structured data into Cognee-friendly text."""

    @staticmethod
    def format_incident(incident: dict[str, Any]) -> str:
        """Format a single incident into natural language text."""
        timeline_text = ""
        if incident.get("timeline"):
            events = []
            for event in incident["timeline"]:
                timestamp = event.get("timestamp", "Unknown time")
                description = event.get("event", "Unknown event")
                events.append(f"  • {timestamp}: {description}")
            timeline_text = "\n".join(events)

        symptoms_text = ""
        if incident.get("symptoms"):
            symptoms_text = "\n".join(f"  • {s}" for s in incident["symptoms"])

        impact = incident.get("impact", {})
        impact_text = (
            f"Impact: {impact.get('users_affected', 0)} users affected, "
            f"${impact.get('revenue_impact_usd', 0):,.0f} revenue impact, "
            f"{impact.get('failed_transactions', 0)} failed transactions"
        )

        return f"""
INCIDENT: {incident.get('title', 'Unknown Incident')}
ID: {incident.get('id', 'Unknown')}
Severity: {incident.get('severity', 'Unknown')}
Timestamp: {incident.get('timestamp', 'Unknown')}
Duration: {incident.get('duration_minutes', 0)} minutes
Status: {incident.get('status', 'Unknown')}
On-Call Engineer: {incident.get('on_call_engineer', 'Unknown')}

Affected Services: {', '.join(incident.get('affected_services', []))}

Symptoms:
{symptoms_text}

Root Cause: {incident.get('root_cause', 'Unknown')}

Resolution: {incident.get('resolution', 'Unknown')}

Timeline:
{timeline_text}

{impact_text}

Tags: {', '.join(incident.get('tags', []))}
Postmortem ID: {incident.get('postmortem_id', 'None')}
""".strip()

    @staticmethod
    def format_service(service: dict[str, Any]) -> str:
        """Format a single service into natural language text."""
        dependencies = ", ".join(service.get("dependencies", []))
        external_apis = ", ".join(service.get("external_apis", []))

        return f"""
SERVICE: {service.get('name', 'Unknown')}
Team: {service.get('team', 'Unknown')}
Description: {service.get('description', 'No description')}
Language: {service.get('language', 'Unknown')}
Framework: {service.get('framework', 'Unknown')}
Database: {service.get('database', 'None')}
Cache: {service.get('cache', 'None')}
Message Queue: {service.get('message_queue', 'None')}

Dependencies: {dependencies if dependencies else 'None'}
External APIs: {external_apis if external_apis else 'None'}

Infrastructure:
  Port: {service.get('port', 'Unknown')}
  Replicas: {service.get('replicas', 1)}
  CPU Limit: {service.get('cpu_limit', 'Unknown')}
  Memory Limit: {service.get('memory_limit', 'Unknown')}
  Health Check: {service.get('health_check', '/health')}

Criticality: {service.get('criticality', 'Unknown')}
SLA: {service.get('sla', 'Unknown')}
Runbook: {service.get('runbook', 'None')}
""".strip()

    @staticmethod
    def format_team(team: dict[str, Any]) -> str:
        """Format a single team into natural language text."""
        members = ", ".join(team.get("members", []))
        services = ", ".join(team.get("services", []))

        return f"""
TEAM: {team.get('display_name', 'Unknown')}
Internal Name: {team.get('name', 'Unknown')}
Description: {team.get('description', 'No description')}
Lead: {team.get('lead', 'Unknown')}
Members: {members if members else 'None'}

Services Owned: {services if services else 'None'}

On-Call Rotation: {team.get('on_call_rotation', 'None')}
Slack Channel: {team.get('slack_channel', 'None')}
PagerDuty Service: {team.get('pagerduty_service', 'None')}
""".strip()

    @staticmethod
    def format_runbook(runbook: dict[str, Any]) -> str:
        """Format a single runbook into natural language text."""
        sections_text = []
        for section in runbook.get("sections", []):
            sections_text.append(f"\n{section.get('title', 'Unknown Section')}:\n{section.get('content', 'No content')}")

        return f"""
RUNBOOK: {runbook.get('title', 'Unknown')}
ID: {runbook.get('id', 'Unknown')}
Service: {runbook.get('service', 'Unknown')}
{"".join(sections_text)}
""".strip()

    @staticmethod
    def format_postmortem(postmortem: dict[str, Any]) -> str:
        """Format a single postmortem into natural language text."""
        rca = postmortem.get("root_cause_analysis", {})
        contributing_factors = "\n".join(
            f"  • {factor}" for factor in rca.get("contributing_factors", [])
        )

        impact = postmortem.get("impact_assessment", {})
        resolution = postmortem.get("resolution", {})

        action_items_text = []
        for item in postmortem.get("action_items", []):
            status = item.get("status", "pending")
            action_items_text.append(
                f"  • [{status.upper()}] {item.get('description', 'Unknown')} "
                f"(Owner: {item.get('owner', 'Unassigned')})"
            )

        action_items_str = (
            "\n".join(action_items_text) if action_items_text else "No action items listed."
        )

        lessons_text = "\n".join(
            f"  • {lesson}" for lesson in postmortem.get("lessons_learned", [])
        )

        preventive_text = "\n".join(
            f"  • {measure}" for measure in postmortem.get("preventive_measures", [])
        )

        return f"""
POSTMORTEM: {postmortem.get('title', 'Unknown')}
ID: {postmortem.get('id', 'Unknown')}
Incident ID: {postmortem.get('incident_id', 'Unknown')}
Date: {postmortem.get('date', 'Unknown')}
Author: {postmortem.get('author', 'Unknown')}
Severity: {postmortem.get('severity', 'Unknown')}

Summary: {postmortem.get('summary', 'No summary')}

Root Cause Analysis:
  Direct Cause: {rca.get('direct_cause', 'Unknown')}
  
  Contributing Factors:
{contributing_factors}

  Why It Happened: {rca.get('why_it_happened', 'Unknown')}

Impact Assessment:
  Duration: {impact.get('duration_minutes', 0)} minutes
  Users Affected: {impact.get('users_affected', 0)}
  Revenue Impact: ${impact.get('revenue_impact_usd', 0):,.0f}
  Failed Transactions: {impact.get('failed_transactions', 0)}
  Customer Complaints: {impact.get('customer_complaints', 0)}
  Data Loss: {'Yes' if impact.get('data_loss') else 'No'}

Resolution:
  Immediate Action: {resolution.get('immediate_action', 'Unknown')}
  Long-Term Fix: {resolution.get('long_term_fix', 'None')}

Action Items:
{action_items_str}

Lessons Learned:
{lessons_text}

Preventive Measures:
{preventive_text}

Follow-Up Notes: {postmortem.get('follow_up_notes', 'None')}
""".strip()


class IngestionEngine:
    """
    Ingestion engine for loading DevOps data into Cognee knowledge graph.

    Handles:
    - Reading JSON datasets
    - Validating data with Pydantic models
    - Formatting data into Cognee-friendly text
    - Ingesting via Cognee Cloud API with proper temporal awareness
    """

    def __init__(self, cognee_client: CogneeClient | None = None) -> None:
        """Initialize ingestion engine."""
        self.settings = get_settings()
        self.cognee = cognee_client or get_cognee_client()
        self.formatter = DataFormatter()

    async def ingest_incidents(
        self,
        data_path: Path | None = None,
        dataset_name: str | None = None,
    ) -> int:
        """
        Ingest incident data into Cognee with temporal awareness.

        Args:
            data_path: Path to incidents JSON file
            dataset_name: Cognee dataset name

        Returns:
            Number of incidents ingested

        Raises:
            IngestionError: If ingestion fails
        """
        data_path = data_path or self.settings.incidents_data_path
        dataset_name = dataset_name or self.settings.incidents_dataset

        logger.info("Starting incident ingestion", path=str(data_path), dataset=dataset_name)

        try:
            # Load and validate data
            with open(data_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            dataset = IncidentDataset.model_validate(raw_data)
            incidents = [incident.model_dump() for incident in dataset.incidents]

            logger.info(f"Loaded {len(incidents)} incidents")

            # Format incidents into text
            formatted_incidents = [
                self.formatter.format_incident(incident) for incident in incidents
            ]

            # Ingest with temporal awareness
            await self.cognee.remember(
                data=formatted_incidents,
                dataset_name=dataset_name,
                temporal_cognify=True,  # Enable temporal awareness for incident timelines
                node_set=["incidents", "devops"],
                self_improvement=False,
            )

            logger.info(f"Successfully ingested {len(incidents)} incidents")
            return len(incidents)

        except FileNotFoundError as e:
            logger.error("Incidents data file not found", path=str(data_path))
            raise IngestionError(
                f"Incidents data file not found: {data_path}",
                source="incidents",
            ) from e
        except Exception as e:
            logger.error("Failed to ingest incidents", error=str(e))
            raise IngestionError(
                f"Failed to ingest incidents: {e}",
                source="incidents",
            ) from e

    async def ingest_architecture(
        self,
        data_path: Path | None = None,
        dataset_name: str | None = None,
    ) -> int:
        """
        Ingest architecture data (services, teams, runbooks) into Cognee.

        Args:
            data_path: Path to architecture JSON file
            dataset_name: Cognee dataset name

        Returns:
            Total number of items ingested

        Raises:
            IngestionError: If ingestion fails
        """
        data_path = data_path or self.settings.architecture_data_path
        dataset_name = dataset_name or self.settings.architecture_dataset

        logger.info("Starting architecture ingestion", path=str(data_path), dataset=dataset_name)

        try:
            # Load and validate data
            with open(data_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            dataset = ArchitectureDataset.model_validate(raw_data)

            # Format all components
            all_items: list[str] = []

            # Services
            services = [service.model_dump() for service in dataset.services]
            formatted_services = [
                self.formatter.format_service(service) for service in services
            ]
            all_items.extend(formatted_services)
            logger.info(f"Formatted {len(services)} services")

            # Teams
            teams = [team.model_dump() for team in dataset.teams]
            formatted_teams = [self.formatter.format_team(team) for team in teams]
            all_items.extend(formatted_teams)
            logger.info(f"Formatted {len(teams)} teams")

            # Runbooks
            runbooks = [runbook.model_dump() for runbook in dataset.runbooks]
            formatted_runbooks = [
                self.formatter.format_runbook(runbook) for runbook in runbooks
            ]
            all_items.extend(formatted_runbooks)
            logger.info(f"Formatted {len(runbooks)} runbooks")

            # Ingest all architecture data
            await self.cognee.remember(
                data=all_items,
                dataset_name=dataset_name,
                temporal_cognify=False,  # No temporal awareness needed for architecture
                node_set=["architecture", "services", "teams", "runbooks", "devops"],
                self_improvement=False,
            )

            total_items = len(services) + len(teams) + len(runbooks)
            logger.info(f"Successfully ingested {total_items} architecture items")
            return total_items

        except FileNotFoundError as e:
            logger.error("Architecture data file not found", path=str(data_path))
            raise IngestionError(
                f"Architecture data file not found: {data_path}",
                source="architecture",
            ) from e
        except Exception as e:
            logger.error("Failed to ingest architecture", error=str(e))
            raise IngestionError(
                f"Failed to ingest architecture: {e}",
                source="architecture",
            ) from e

    async def ingest_postmortems(
        self,
        data_path: Path | None = None,
        dataset_name: str | None = None,
    ) -> int:
        """
        Ingest postmortem data into Cognee.

        Args:
            data_path: Path to postmortems JSON file
            dataset_name: Cognee dataset name

        Returns:
            Number of postmortems ingested

        Raises:
            IngestionError: If ingestion fails
        """
        data_path = data_path or self.settings.postmortem_data_path
        dataset_name = dataset_name or self.settings.postmortems_dataset

        logger.info("Starting postmortem ingestion", path=str(data_path), dataset=dataset_name)

        try:
            # Load and validate data
            with open(data_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            dataset = PostmortemDataset.model_validate(raw_data)
            postmortems = [pm.model_dump() for pm in dataset.postmortems]

            logger.info(f"Loaded {len(postmortems)} postmortems")

            # Format postmortems into text
            formatted_postmortems = [
                self.formatter.format_postmortem(pm) for pm in postmortems
            ]

            # Ingest postmortems
            await self.cognee.remember(
                data=formatted_postmortems,
                dataset_name=dataset_name,
                temporal_cognify=True,  # Enable temporal awareness for postmortem dates
                node_set=["postmortems", "devops"],
                self_improvement=False,
            )

            logger.info(f"Successfully ingested {len(postmortems)} postmortems")
            return len(postmortems)

        except FileNotFoundError as e:
            logger.error("Postmortems data file not found", path=str(data_path))
            raise IngestionError(
                f"Postmortems data file not found: {data_path}",
                source="postmortems",
            ) from e
        except Exception as e:
            logger.error("Failed to ingest postmortems", error=str(e))
            raise IngestionError(
                f"Failed to ingest postmortems: {e}",
                source="postmortems",
            ) from e

    async def ingest_all(self) -> dict[str, int]:
        """
        Ingest all datasets (incidents, architecture, postmortems).

        Returns:
            Dictionary with counts for each dataset type

        Raises:
            IngestionError: If any ingestion fails
        """
        logger.info("Starting full data ingestion")

        results = {
            "incidents": await self.ingest_incidents(),
            "architecture": await self.ingest_architecture(),
            "postmortems": await self.ingest_postmortems(),
        }

        total = sum(results.values())
        logger.info(f"Full ingestion complete. Total items: {total}", results=results)

        return results
