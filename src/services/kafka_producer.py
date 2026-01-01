"""Direct Kafka producer as fallback when Dapr is unavailable."""

import json
import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Flag to check if kafka-python is available
KAFKA_AVAILABLE = False

try:
    from kafka import KafkaProducer
    from kafka.errors import KafkaError
    KAFKA_AVAILABLE = True
except ImportError:
    logger.warning("kafka-python not installed. Kafka direct publishing disabled.")


class DirectKafkaProducer:
    """Direct Kafka producer for publishing events without Dapr."""

    def __init__(self):
        self.producer: Optional[KafkaProducer] = None
        self.enabled = KAFKA_AVAILABLE

        if self.enabled:
            try:
                bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
                self.producer = KafkaProducer(
                    bootstrap_servers=bootstrap_servers.split(","),
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                    key_serializer=lambda k: k.encode('utf-8') if k else None
                )
                logger.info(f"Direct Kafka producer initialized: {bootstrap_servers}")
            except Exception as e:
                logger.error(f"Failed to initialize Kafka producer: {e}")
                self.enabled = False

    def publish_task_event(
        self,
        event_type: str,
        task_id: int,
        task_data: Dict[str, Any],
        user_id: str = "anonymous"
    ) -> bool:
        """Publish task event directly to Kafka.

        Args:
            event_type: Event type (task.created, task.updated, etc.)
            task_id: Task ID
            task_data: Task data
            user_id: User ID

        Returns:
            True if published successfully
        """
        if not self.enabled or not self.producer:
            return False

        event = {
            "type": event_type,
            "task_id": task_id,
            "data": task_data,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        try:
            future = self.producer.send(
                topic="todo-events",
                key=str(task_id),
                value=event
            )

            # Wait for confirmation (non-blocking with timeout)
            future.get(timeout=2)
            logger.info(f"Published event to Kafka: {event_type} for task {task_id}")
            return True

        except KafkaError as e:
            logger.error(f"Kafka error publishing event: {e}")
            return False
        except Exception as e:
            logger.error(f"Error publishing to Kafka: {e}")
            return False

    def close(self):
        """Close the Kafka producer."""
        if self.producer:
            self.producer.flush()
            self.producer.close()


# Global instance
_kafka_producer: Optional[DirectKafkaProducer] = None


def get_kafka_producer() -> DirectKafkaProducer:
    """Get or create the global Kafka producer."""
    global _kafka_producer
    if _kafka_producer is None:
        _kafka_producer = DirectKafkaProducer()
    return _kafka_producer


def close_kafka_producer():
    """Close the global Kafka producer."""
    global _kafka_producer
    if _kafka_producer:
        _kafka_producer.close()
        _kafka_producer = None
