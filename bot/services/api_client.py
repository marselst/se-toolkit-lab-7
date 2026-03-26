"""LMS API client for communicating with the backend."""

from dataclasses import dataclass
from typing import Any

import httpx


class APIError(Exception):
    """Exception raised when API request fails."""

    def __init__(self, message: str, original_error: Exception | None = None):
        self.message = message
        self.original_error = original_error
        super().__init__(self.message)


@dataclass
class LabItem:
    """Represents a lab or task item from the backend."""

    id: int
    title: str
    type: str
    description: str = ""
    parent_id: int | None = None


@dataclass
class PassRate:
    """Represents pass rate data for a task."""

    task: str
    avg_score: float
    attempts: int


class APIClient:
    """Client for the LMS backend API."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=10.0,
        )

    def _request(self, method: str, path: str, params: dict | None = None) -> Any:
        """Make an API request with error handling.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path (e.g., "/items/")
            params: Optional query parameters

        Returns:
            JSON response data

        Raises:
            APIError: If the request fails
        """
        try:
            response = self._client.request(method, path, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise APIError(
                f"HTTP {e.response.status_code} {e.response.reason_phrase}. "
                f"The backend returned an error for {path}."
            ) from e
        except httpx.ConnectError as e:
            raise APIError(
                f"Connection refused ({self.base_url}). "
                "Check that the backend service is running."
            ) from e
        except httpx.TimeoutException as e:
            raise APIError(
                f"Request timed out ({self.base_url}). "
                "The backend may be overloaded."
            ) from e
        except Exception as e:
            raise APIError(f"Unexpected error: {e}") from e

    def get_items(self) -> list[LabItem]:
        """Get all items (labs and tasks) from the backend.

        Returns:
            List of LabItem objects
        """
        data = self._request("GET", "/items/")
        return [
            LabItem(
                id=item["id"],
                title=item["title"],
                type=item["type"],
                description=item.get("description", ""),
                parent_id=item.get("parent_id"),
            )
            for item in data
        ]

    def get_pass_rates(self, lab: str) -> list[PassRate]:
        """Get pass rates for a specific lab.

        Args:
            lab: Lab identifier (e.g., "lab-04")

        Returns:
            List of PassRate objects
        """
        data = self._request("GET", "/analytics/pass-rates", params={"lab": lab})
        return [
            PassRate(
                task=item["task"],
                avg_score=item["avg_score"],
                attempts=item["attempts"],
            )
            for item in data
        ]

    def check_health(self) -> tuple[bool, str, int]:
        """Check if the backend is healthy.

        Returns:
            Tuple of (is_healthy, message, item_count)
        """
        try:
            items = self.get_items()
            return True, f"Backend is healthy. {len(items)} items available.", len(items)
        except APIError as e:
            return False, f"Backend error: {e.message}", 0

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()
