"""Health check endpoints for Kubernetes probes."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Health check endpoint for Kubernetes liveness probe.
    Returns 200 OK if the service is running.
    """
    return {"status": "healthy", "service": "todo-backend"}


@router.get("/ready")
async def readiness_check():
    """
    Readiness check endpoint for Kubernetes readiness probe.
    Returns 200 OK if the service is ready to accept traffic.

    In a more complex app, this would check database connections,
    external service availability, etc.
    """
    return {"status": "ready", "service": "todo-backend"}
