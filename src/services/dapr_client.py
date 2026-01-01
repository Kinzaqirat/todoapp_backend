"""Dapr client service for pub/sub, state store, and secrets management."""

import os
import json
import httpx
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class DaprTopic(str, Enum):
    """Kafka topics for TaskFlow events."""
    TASK_EVENTS = "task-events"
    REMINDERS = "reminders"
    TASK_UPDATES = "task-updates"
    AUDIT_LOGS = "audit-logs"


@dataclass
class DaprConfig:
    """Dapr configuration."""
    http_port: int = 3500
    grpc_port: int = 50001
    pubsub_name: str = "kafka-pubsub"
    statestore_name: str = "statestore"
    secret_store_name: str = "kubernetes-secrets"

    @classmethod
    def from_env(cls) -> "DaprConfig":
        """Create config from environment variables."""
        return cls(
            http_port=int(os.getenv("DAPR_HTTP_PORT", "3500")),
            grpc_port=int(os.getenv("DAPR_GRPC_PORT", "50001")),
            pubsub_name=os.getenv("PUBSUB_NAME", "kafka-pubsub"),
            statestore_name=os.getenv("STATESTORE_NAME", "statestore"),
            secret_store_name=os.getenv("SECRET_STORE_NAME", "kubernetes-secrets"),
        )


class DaprClient:
    """HTTP client for Dapr sidecar communication."""

    def __init__(self, config: Optional[DaprConfig] = None):
        self.config = config or DaprConfig.from_env()
        self.base_url = f"http://localhost:{self.config.http_port}"
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # --- Pub/Sub Methods ---

    async def publish_event(
        self,
        topic: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, str]] = None
    ) -> bool:
        """Publish an event to a Kafka topic via Dapr.

        Args:
            topic: The topic name (e.g., "task-events")
            data: The event payload
            metadata: Optional metadata for the message

        Returns:
            True if published successfully, False otherwise
        """
        client = await self._get_client()
        url = f"{self.base_url}/v1.0/publish/{self.config.pubsub_name}/{topic}"

        headers = {"Content-Type": "application/json"}
        if metadata:
            for key, value in metadata.items():
                headers[f"metadata.{key}"] = value

        try:
            response = await client.post(url, json=data, headers=headers)
            if response.status_code in (200, 204):
                logger.info(f"Published event to topic '{topic}': {data.get('type', 'unknown')}")
                return True
            else:
                logger.error(f"Failed to publish event: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error publishing event to '{topic}': {e}")
            return False

    async def publish_task_event(
        self,
        event_type: str,
        task_id: int,
        task_data: Dict[str, Any],
        user_id: str = "anonymous"
    ) -> bool:
        """Publish a task event.

        Args:
            event_type: Type of event (task.created, task.updated, etc.)
            task_id: The task ID
            task_data: The task data
            user_id: The user who triggered the event

        Returns:
            True if published successfully
        """
        event = {
            "type": event_type,
            "task_id": task_id,
            "data": task_data,
            "user_id": user_id,
            "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z"
        }
        return await self.publish_event(DaprTopic.TASK_EVENTS.value, event)

    # --- State Store Methods ---

    async def get_state(self, key: str) -> Optional[Any]:
        """Get a value from the state store.

        Args:
            key: The state key

        Returns:
            The stored value or None if not found
        """
        client = await self._get_client()
        url = f"{self.base_url}/v1.0/state/{self.config.statestore_name}/{key}"

        try:
            response = await client.get(url)
            if response.status_code == 200:
                return response.json() if response.content else None
            elif response.status_code == 204:
                return None
            else:
                logger.error(f"Failed to get state '{key}': {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error getting state '{key}': {e}")
            return None

    async def set_state(
        self,
        key: str,
        value: Any,
        metadata: Optional[Dict[str, str]] = None
    ) -> bool:
        """Save a value to the state store.

        Args:
            key: The state key
            value: The value to store
            metadata: Optional metadata (e.g., TTL)

        Returns:
            True if saved successfully
        """
        client = await self._get_client()
        url = f"{self.base_url}/v1.0/state/{self.config.statestore_name}"

        state_item = {
            "key": key,
            "value": value
        }
        if metadata:
            state_item["metadata"] = metadata

        try:
            response = await client.post(url, json=[state_item])
            if response.status_code in (200, 201, 204):
                logger.debug(f"Saved state '{key}'")
                return True
            else:
                logger.error(f"Failed to save state '{key}': {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error saving state '{key}': {e}")
            return False

    async def delete_state(self, key: str) -> bool:
        """Delete a value from the state store.

        Args:
            key: The state key

        Returns:
            True if deleted successfully
        """
        client = await self._get_client()
        url = f"{self.base_url}/v1.0/state/{self.config.statestore_name}/{key}"

        try:
            response = await client.delete(url)
            return response.status_code in (200, 204)
        except Exception as e:
            logger.error(f"Error deleting state '{key}': {e}")
            return False

    async def get_bulk_state(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from the state store.

        Args:
            keys: List of state keys

        Returns:
            Dictionary of key-value pairs
        """
        client = await self._get_client()
        url = f"{self.base_url}/v1.0/state/{self.config.statestore_name}/bulk"

        try:
            response = await client.post(url, json={"keys": keys})
            if response.status_code == 200:
                results = response.json()
                return {item["key"]: item.get("data") for item in results}
            return {}
        except Exception as e:
            logger.error(f"Error getting bulk state: {e}")
            return {}

    # --- Secrets Methods ---

    async def get_secret(self, secret_name: str, key: Optional[str] = None) -> Optional[str]:
        """Get a secret from the secret store.

        Args:
            secret_name: The secret name
            key: Optional key within the secret

        Returns:
            The secret value or None if not found
        """
        client = await self._get_client()
        url = f"{self.base_url}/v1.0/secrets/{self.config.secret_store_name}/{secret_name}"

        try:
            response = await client.get(url)
            if response.status_code == 200:
                secrets = response.json()
                if key:
                    return secrets.get(key)
                return secrets.get(secret_name)
            return None
        except Exception as e:
            logger.error(f"Error getting secret '{secret_name}': {e}")
            return None

    # --- Health Check ---

    async def health_check(self) -> bool:
        """Check if Dapr sidecar is healthy.

        Returns:
            True if healthy
        """
        client = await self._get_client()
        url = f"{self.base_url}/v1.0/healthz"

        try:
            response = await client.get(url)
            return response.status_code == 200
        except Exception:
            return False


# Global client instance
_dapr_client: Optional[DaprClient] = None


def get_dapr_client() -> DaprClient:
    """Get the global Dapr client instance."""
    global _dapr_client
    if _dapr_client is None:
        _dapr_client = DaprClient()
    return _dapr_client


async def close_dapr_client():
    """Close the global Dapr client."""
    global _dapr_client
    if _dapr_client:
        await _dapr_client.close()
        _dapr_client = None
