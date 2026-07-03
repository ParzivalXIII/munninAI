"""
Forge Custom Exceptions

Custom exception hierarchy for the Forge application.
"""

from typing import Any


class ForgeError(Exception):
    """Base exception for all Forge errors."""

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}

    def __str__(self) -> str:
        base = f"{self.__class__.__name__}: {self.message}"
        if self.error_code:
            base += f" (Code: {self.error_code})"
        if self.details:
            base += f" Details: {self.details}"
        return base


class ConfigurationError(ForgeError):
    """Configuration-related errors."""

    def __init__(
        self,
        message: str,
        field_name: str | None = None,
        error_code: str = "CONFIGURATION_ERROR",
    ) -> None:
        details = {"field_name": field_name} if field_name else None
        super().__init__(message, error_code, details)


class CogneeConnectionError(ForgeError):
    """Failed to connect to Cognee Cloud."""

    def __init__(self, message: str, error_code: str = "COGNEE_CONNECTION_ERROR") -> None:
        super().__init__(message, error_code)


class CogneeAPIError(ForgeError):
    """Cognee Cloud API returned an error."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        error_code: str = "COGNEE_API_ERROR",
    ) -> None:
        details = {"status_code": status_code} if status_code else None
        super().__init__(message, error_code, details)


class DatasetNotFoundError(ForgeError):
    """Requested dataset not found in Cognee."""

    def __init__(
        self,
        dataset_name: str,
        error_code: str = "DATASET_NOT_FOUND",
    ) -> None:
        super().__init__(
            f"Dataset '{dataset_name}' not found",
            error_code,
            {"dataset_name": dataset_name},
        )


class IngestionError(ForgeError):
    """Error during data ingestion."""

    def __init__(
        self,
        message: str,
        source: str | None = None,
        error_code: str = "INGESTION_ERROR",
    ) -> None:
        details = {"source": source} if source else None
        super().__init__(message, error_code, details)


class AgentError(ForgeError):
    """Error in agent execution."""

    def __init__(
        self,
        message: str,
        agent_name: str | None = None,
        error_code: str = "AGENT_ERROR",
    ) -> None:
        details = {"agent_name": agent_name} if agent_name else None
        super().__init__(message, error_code, details)


class RecallError(ForgeError):
    """Error during memory recall."""

    def __init__(
        self,
        message: str,
        query_text: str | None = None,
        error_code: str = "RECALL_ERROR",
    ) -> None:
        details = {"query_text": query_text} if query_text else None
        super().__init__(message, error_code, details)
