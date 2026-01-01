"""Audit API endpoints for querying audit logs."""

from fastapi import APIRouter, Query
from typing import Optional, List
from ..services.audit import audit_service, AuditEventType

router = APIRouter()


@router.get("/")
async def get_audit_logs(
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    entity_id: Optional[int] = Query(None, description="Filter by entity ID"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of logs to return"),
    offset: int = Query(0, ge=0, description="Number of logs to skip"),
):
    """Get audit logs with optional filters.

    Returns audit log entries in reverse chronological order (newest first).
    """
    # Convert event_type string to enum if provided
    event_type_enum = None
    if event_type:
        try:
            event_type_enum = AuditEventType(event_type)
        except ValueError:
            pass  # Invalid event type, will return all

    logs = audit_service.get_logs(
        event_type=event_type_enum,
        entity_id=entity_id,
        user_id=user_id,
        limit=limit,
        offset=offset,
    )

    return {
        "logs": [log.to_dict() for log in logs],
        "count": len(logs),
        "limit": limit,
        "offset": offset,
    }


@router.get("/task/{task_id}")
async def get_task_audit_history(
    task_id: int,
    limit: int = Query(50, ge=1, le=500),
):
    """Get audit history for a specific task."""
    logs = audit_service.get_task_history(task_id, limit=limit)
    return {
        "task_id": task_id,
        "logs": [log.to_dict() for log in logs],
        "count": len(logs),
    }


@router.get("/event-types")
async def get_event_types():
    """Get all available audit event types."""
    return {
        "event_types": [e.value for e in AuditEventType]
    }


@router.get("/stats")
async def get_audit_stats():
    """Get audit log statistics."""
    all_logs = audit_service.get_logs(limit=10000)

    # Count by event type
    event_counts = {}
    for log in all_logs:
        event_type = log.event_type.value if isinstance(log.event_type, AuditEventType) else log.event_type
        event_counts[event_type] = event_counts.get(event_type, 0) + 1

    return {
        "total_logs": len(all_logs),
        "by_event_type": event_counts,
    }
