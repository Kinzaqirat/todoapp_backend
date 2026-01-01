"""WebSocket endpoint for real-time task synchronization."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set
import json
import asyncio

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections for real-time sync."""

    def __init__(self):
        # Map of user_id to set of active WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # All connections (for broadcast)
        self.all_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket, user_id: str = "anonymous"):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.all_connections.add(websocket)

        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)

    def disconnect(self, websocket: WebSocket, user_id: str = "anonymous"):
        """Remove a WebSocket connection."""
        self.all_connections.discard(websocket)

        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_personal_message(self, message: dict, user_id: str):
        """Send a message to all connections of a specific user."""
        if user_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.append(connection)

            # Clean up disconnected
            for conn in disconnected:
                self.disconnect(conn, user_id)

    async def broadcast(self, message: dict):
        """Broadcast a message to all connected clients."""
        disconnected = []
        for connection in self.all_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)

        # Clean up disconnected
        for conn in disconnected:
            self.all_connections.discard(conn)

    def get_connection_count(self) -> int:
        """Get the total number of active connections."""
        return len(self.all_connections)


# Global connection manager instance
manager = ConnectionManager()


async def notify_task_change(event_type: str, task_data: dict, user_id: str = "anonymous"):
    """Notify all clients about a task change.

    Args:
        event_type: Type of event (task.created, task.updated, task.deleted, task.completed)
        task_data: The task data to send
        user_id: The user who made the change
    """
    message = {
        "type": event_type,
        "data": task_data,
        "user_id": user_id
    }
    await manager.broadcast(message)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, user_id: str = "anonymous"):
    """WebSocket endpoint for real-time task updates.

    Connect to this endpoint to receive real-time task updates.
    Events sent:
    - task.created: A new task was created
    - task.updated: A task was updated
    - task.deleted: A task was deleted
    - task.completed: A task was marked as complete

    Query Parameters:
        user_id: Optional user identifier for targeted messages
    """
    await manager.connect(websocket, user_id)

    try:
        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to TaskFlow real-time sync",
            "connections": manager.get_connection_count()
        })

        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()

            try:
                message = json.loads(data)

                # Handle ping/pong for keep-alive
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})

                # Handle subscription requests (for future use)
                elif message.get("type") == "subscribe":
                    await websocket.send_json({
                        "type": "subscribed",
                        "channel": message.get("channel", "tasks")
                    })

            except json.JSONDecodeError:
                # If not JSON, treat as ping
                if data == "ping":
                    await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
    except Exception:
        manager.disconnect(websocket, user_id)


@router.get("/ws/status")
async def websocket_status():
    """Get WebSocket connection status."""
    return {
        "active_connections": manager.get_connection_count(),
        "status": "healthy"
    }
