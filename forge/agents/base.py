"""
Base Agent Module

Common functionality for all Forge agents.
"""

from uuid import uuid4

import structlog

from forge.core.cognee_client import CogneeClient, get_cognee_client
from forge.core.config import get_settings

logger = structlog.get_logger(__name__)


class BaseAgent:
    """
    Base class for all Forge agents.

    Provides common functionality:
    - Cognee client management
    - Session ID generation
    - Dataset configuration
    - Logging
    """

    def __init__(
        self,
        name: str,
        cognee_client: CogneeClient | None = None,
    ) -> None:
        """
        Initialize base agent.

        Args:
            name: Agent name for logging and session tracking
            cognee_client: Optional Cognee client instance
        """
        self.name = name
        self.settings = get_settings()
        self.cognee = cognee_client or get_cognee_client()
        self.logger = logger.bind(agent_name=name)

    def generate_session_id(self, prefix: str = "session") -> str:
        """
        Generate a unique session ID.

        Args:
            prefix: Optional prefix for the session ID

        Returns:
            Unique session ID string
        """
        return f"{prefix}_{uuid4().hex[:8]}"

    def get_all_datasets(self) -> list[str]:
        """
        Get all configured dataset names.

        Returns:
            List of dataset names
        """
        return [
            self.settings.incidents_dataset,
            self.settings.architecture_dataset,
            self.settings.postmortems_dataset,
        ]

    async def ensure_connected(self) -> None:
        """Ensure Cognee client is connected."""
        if not self.cognee.is_connected:
            await self.cognee.connect()
            self.logger.info("Connected to Cognee Cloud")
