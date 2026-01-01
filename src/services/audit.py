"""Audit logging service for tracking task operations."""

import json
import logging
import os
from datetime import datetime
from typing import Optional, Any, Dict, List
from pathlib import Path
from enum import Enum


class AuditEventType(str, Enum):
    """Types of audit events."""
    TASK_CREATED = "task.created"
    TASK_UPDATED = "task.updated"
    TASK_DELETED = "task.deleted"
    TASK_COMPLETED = "task.completed"
    TASK_UNCOMPLETED = "task.uncompleted"
    TASK_SEARCHED = "task.searched"
    CHAT_MESSAGE = "chat.message"


class AuditLog:
    """Represents a single audit log entry."""

    def __init__(
        self,
        event_type: AuditEventType,
        entity_id: Optional[int] = None,
        entity_type: str = "task",
        user_id: str = "anonymous",
        changes: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.id = None  # Set when saved
        self.timestamp = datetime.now()
        self.event_type = event_type
        self.entity_id = entity_id
        self.entity_type = entity_type
        self.user_id = user_id
        self.changes = changes or {}
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value if isinstance(self.event_type, AuditEventType) else self.event_type,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "user_id": self.user_id,
            "changes": self.changes,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditLog":
        """Create from dictionary."""
        log = cls(
            event_type=data["event_type"],
            entity_id=data.get("entity_id"),
            entity_type=data.get("entity_type", "task"),
            user_id=data.get("user_id", "anonymous"),
            changes=data.get("changes", {}),
            metadata=data.get("metadata", {}),
        )
        log.id = data.get("id")
        if data.get("timestamp"):
            log.timestamp = datetime.fromisoformat(data["timestamp"])
        return log


class AuditService:
    """Service for managing audit logs."""

    def __init__(self, storage_path: Optional[str] = None):
        # Use env var if available, otherwise use provided path or default
        default_path = os.getenv("AUDIT_LOGS_PATH", "audit_logs.json")
        self.storage_path = Path(storage_path or default_path)
        # Ensure directory exists
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger("audit")
        self._logs: List[AuditLog] = []
        self._load_logs()

    def _load_logs(self) -> None:
        """Load audit logs from storage."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r") as f:
                    data = json.load(f)
                    self._logs = [AuditLog.from_dict(log) for log in data]
            except (json.JSONDecodeError, IOError) as e:
                self.logger.error(f"Failed to load audit logs: {e}")
                self._logs = []
        else:
            self._logs = []

    def _save_logs(self) -> None:
        """Save audit logs to storage."""
        try:
            with open(self.storage_path, "w") as f:
                json.dump([log.to_dict() for log in self._logs], f, indent=2)
        except IOError as e:
            self.logger.error(f"Failed to save audit logs: {e}")

    def _get_next_id(self) -> int:
        """Get the next available ID."""
        if not self._logs:
            return 1
        return max(log.id or 0 for log in self._logs) + 1

    def log(
        self,
        event_type: AuditEventType,
        entity_id: Optional[int] = None,
        entity_type: str = "task",
        user_id: str = "anonymous",
        changes: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Create and store a new audit log entry."""
        log = AuditLog(
            event_type=event_type,
            entity_id=entity_id,
            entity_type=entity_type,
            user_id=user_id,
            changes=changes,
            metadata=metadata,
        )
        log.id = self._get_next_id()

        self._logs.append(log)
        self._save_logs()

        # Also log to standard logging
        self.logger.info(
            f"AUDIT: {event_type.value if isinstance(event_type, AuditEventType) else event_type} "
            f"entity={entity_type}:{entity_id} user={user_id}"
        )

        return log

    def log_task_created(self, task_id: int, task_data: Dict[str, Any], user_id: str = "anonymous") -> AuditLog:
        """Log task creation."""
        return self.log(
            event_type=AuditEventType.TASK_CREATED,
            entity_id=task_id,
            user_id=user_id,
            changes={"new": task_data},
        )

    def log_task_updated(
        self,
        task_id: int,
        old_data: Dict[str, Any],
        new_data: Dict[str, Any],
        user_id: str = "anonymous"
    ) -> AuditLog:
        """Log task update."""
        # Calculate what changed
        changes = {}
        for key in set(old_data.keys()) | set(new_data.keys()):
            old_val = old_data.get(key)
            new_val = new_data.get(key)
            if old_val != new_val:
                changes[key] = {"old": old_val, "new": new_val}

        return self.log(
            event_type=AuditEventType.TASK_UPDATED,
            entity_id=task_id,
            user_id=user_id,
            changes=changes,
        )

    def log_task_deleted(self, task_id: int, task_data: Dict[str, Any], user_id: str = "anonymous") -> AuditLog:
        """Log task deletion."""
        return self.log(
            event_type=AuditEventType.TASK_DELETED,
            entity_id=task_id,
            user_id=user_id,
            changes={"deleted": task_data},
        )

    def log_task_completed(self, task_id: int, task_title: str, user_id: str = "anonymous") -> AuditLog:
        """Log task completion."""
        return self.log(
            event_type=AuditEventType.TASK_COMPLETED,
            entity_id=task_id,
            user_id=user_id,
            metadata={"title": task_title},
        )

    def log_chat_message(self, message: str, response: str, action: Optional[str] = None, user_id: str = "anonymous") -> AuditLog:
        """Log chat interaction."""
        return self.log(
            event_type=AuditEventType.CHAT_MESSAGE,
            entity_type="chat",
            user_id=user_id,
            metadata={
                "message": message[:500],  # Truncate long messages
                "response": response[:500],
                "action": action,
            },
        )

    def get_logs(
        self,
        event_type: Optional[AuditEventType] = None,
        entity_id: Optional[int] = None,
        user_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditLog]:
        """Query audit logs with optional filters."""
        logs = self._logs

        if event_type:
            logs = [l for l in logs if l.event_type == event_type or l.event_type == event_type.value]

        if entity_id is not None:
            logs = [l for l in logs if l.entity_id == entity_id]

        if user_id:
            logs = [l for l in logs if l.user_id == user_id]

        # Sort by timestamp descending (newest first)
        logs = sorted(logs, key=lambda l: l.timestamp, reverse=True)

        # Apply pagination
        return logs[offset:offset + limit]

    def get_task_history(self, task_id: int, limit: int = 50) -> List[AuditLog]:
        """Get all audit logs for a specific task."""
        return self.get_logs(entity_id=task_id, limit=limit)

    def clear_logs(self) -> None:
        """Clear all audit logs (use with caution)."""
        self._logs = []
        self._save_logs()


# Global audit service instance
audit_service = AuditService()
