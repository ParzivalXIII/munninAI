"""
Cognee Cloud Client Wrapper

Provides a clean interface to Cognee Cloud's memory operations.
Handles connection, authentication, and error handling.
"""

import asyncio
from typing import Any

import cognee
import structlog
from cognee import SearchType

from forge.core.config import get_settings
from forge.core.exceptions import (
    CogneeAPIError,
    CogneeConnectionError,
    ConfigurationError,
    DatasetNotFoundError,
)

logger = structlog.get_logger(__name__)


class CogneeClient:
    """
    Wrapper around Cognee Cloud SDK for Forge operations.

    Provides high-level methods for:
    - remember(): Ingest data into knowledge graph
    - recall(): Query the knowledge graph
    - improve(): Enrich and bridge session memory
    - forget(): Remove data from knowledge graph
    """

    def __init__(self) -> None:
        """Initialize the Cognee client with settings."""
        self.settings = get_settings()
        self._connected: bool = False
        self._client: Any = None

    async def connect(self) -> None:
        """
        Connect to Cognee Cloud.

        Raises:
            ConfigurationError: If API keys are not configured
            CogneeConnectionError: If connection fails
        """
        if self._connected:
            logger.debug("Already connected to Cognee Cloud")
            return

        # Validate configuration
        if not self.settings.cognee_api_key or self.settings.cognee_api_key.startswith("REPLACE"):
            raise ConfigurationError(
                "Cognee API key not configured. Set COGNEE_API_KEY in .env",
                field_name="cognee_api_key",
            )

        if not self.settings.llm_api_key or self.settings.llm_api_key.startswith("REPLACE"):
            raise ConfigurationError(
                "LLM API key not configured. Set LLM_API_KEY in .env",
                field_name="llm_api_key",
            )

        try:
            logger.info(
                "Connecting to Cognee Cloud",
                url=self.settings.cognee_service_url,
            )

            # Connect to Cognee Cloud using the serve() method
            self._client = await cognee.serve(
                url=self.settings.cognee_service_url,
                api_key=self.settings.cognee_api_key,
            )

            self._connected = True
            logger.info("Successfully connected to Cognee Cloud")

        except Exception as e:
            logger.error("Failed to connect to Cognee Cloud", error=str(e))
            raise CogneeConnectionError(f"Failed to connect to Cognee Cloud: {e}") from e

    async def disconnect(self) -> None:
        """Disconnect from Cognee Cloud."""
        if not self._connected:
            return

        try:
            await cognee.disconnect()
            self._connected = False
            self._client = None
            logger.info("Disconnected from Cognee Cloud")
        except Exception as e:
            logger.warning("Error during disconnect", error=str(e))

    async def remember(
        self,
        data: str | list[str],
        dataset_name: str,
        temporal_cognify: bool = False,
        node_set: list[str] | None = None,
        session_id: str | None = None,
        self_improvement: bool = True,
    ) -> None:
        """
        Ingest data into Cognee's knowledge graph.

        Args:
            data: Text data to ingest (string or list of strings)
            dataset_name: Name of the dataset to store in
            temporal_cognify: If True, extract temporal information
            node_set: Optional node set tags for organization
            session_id: Optional session ID for session memory
            self_improvement: If True, run self-improvement after ingestion

        Raises:
            CogneeAPIError: If the API call fails
        """
        if not self._connected:
            await self.connect()

        try:
            logger.info(
                "Remembering data",
                dataset=dataset_name,
                temporal=temporal_cognify,
                data_length=len(data) if isinstance(data, list) else len(str(data)),
            )

            await self._client.remember(
                data,
                dataset_name=dataset_name,
                temporal_cognify=temporal_cognify,
                node_set=node_set,
                session_id=session_id,
                self_improvement=self_improvement,
            )

            logger.info("Successfully remembered data", dataset=dataset_name)

        except Exception as e:
            logger.error("Failed to remember data", dataset=dataset_name, error=str(e))
            raise CogneeAPIError(f"Failed to remember data: {e}") from e

    async def recall(
        self,
        query_text: str,
        datasets: list[str] | None = None,
        search_type: SearchType = SearchType.GRAPH_COMPLETION,
        top_k: int = 10,
        node_set: list[str] | None = None,
        session_id: str | None = None,
    ) -> list[Any]:
        """
        Query the knowledge graph.

        Args:
            query_text: Natural language query
            datasets: Optional list of datasets to search in
            search_type: Type of search (GRAPH_COMPLETION, TEMPORAL, etc.)
            top_k: Number of results to return
            node_set: Optional node set filter
            session_id: Optional session ID for conversational context

        Returns:
            List of search results

        Raises:
            CogneeAPIError: If the API call fails
        """
        if not self._connected:
            await self.connect()

        try:
            logger.info(
                "Recalling from knowledge graph",
                query=query_text[:100],
                search_type=search_type.value if hasattr(search_type, "value") else str(search_type),
                datasets=datasets,
            )

            results = await self._client.recall(
                query_text,
                datasets=datasets,
                search_type=search_type,
                top_k=top_k,
                node_name=node_set,
                session_id=session_id,
            )

            logger.info("Recall successful", result_count=len(results))
            return results

        except Exception as e:
            logger.error("Failed to recall from knowledge graph", error=str(e))
            raise CogneeAPIError(f"Failed to recall: {e}") from e

    async def improve(
        self,
        dataset: str,
        session_ids: list[str] | None = None,
        build_truth_subspace: bool = False,
        run_in_background: bool = False,
    ) -> None:
        """
        Enrich existing memory and bridge session content.

        Args:
            dataset: Dataset name to improve
            session_ids: Optional session IDs to bridge into permanent memory
            build_truth_subspace: If True, build truth subspace for reranking
            run_in_background: If True, run asynchronously

        Raises:
            CogneeAPIError: If the API call fails
        """
        if not self._connected:
            await self.connect()

        try:
            logger.info(
                "Improving dataset",
                dataset=dataset,
                session_ids=session_ids,
                build_truth_subspace=build_truth_subspace,
            )

            await self._client.improve(
                dataset=dataset,
                session_ids=session_ids,
                build_truth_subspace=build_truth_subspace,
                run_in_background=run_in_background,
            )

            logger.info("Improve completed", dataset=dataset)

        except Exception as e:
            logger.error("Failed to improve dataset", dataset=dataset, error=str(e))
            raise CogneeAPIError(f"Failed to improve: {e}") from e

    async def forget(
        self,
        dataset: str | None = None,
        everything: bool = False,
    ) -> None:
        """
        Remove data from the knowledge graph.

        Args:
            dataset: Optional dataset name to forget
            everything: If True, forget all data

        Raises:
            CogneeAPIError: If the API call fails
        """
        if not self._connected:
            await self.connect()

        try:
            logger.info("Forgetting data", dataset=dataset, everything=everything)

            await self._client.forget(dataset=dataset, everything=everything)

            logger.info("Forget completed")

        except Exception as e:
            logger.error("Failed to forget data", error=str(e))
            raise CogneeAPIError(f"Failed to forget: {e}") from e

    @property
    def is_connected(self) -> bool:
        """Check if connected to Cognee Cloud."""
        return self._connected


# Global client instance
_client: CogneeClient | None = None


def get_cognee_client() -> CogneeClient:
    """Get the global Cognee client instance."""
    global _client
    if _client is None:
        _client = CogneeClient()
    return _client
