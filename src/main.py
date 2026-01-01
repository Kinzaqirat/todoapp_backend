"""FastAPI application entry point for TaskFlow."""

import os
import sys
# sys.path.append('/app')
# print(f"DEBUG: sys.path: {sys.path}")
# print(f"DEBUG: os.getcwd(): {os.getcwd()}")
# print(f"DEBUG: __name__: {__name__}")
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from src.api import tasks
from src.api import chat
from src.api import health
from src.api import websocket
from src.api import audit

app = FastAPI(
    title="TaskFlow API",
    description="AI-Powered Todo Chatbot Backend",
    version="1.0.0"
)

# CORS middleware - configure from environment
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3001,http://localhost:3000,https://todo-front-ruddy.vercel.app").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(tasks.router, prefix="/api/v1", tags=["tasks"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])

# Health check endpoints for Kubernetes probes
app.include_router(health.router, tags=["health"])

# WebSocket endpoint for
#  real-time sync
app.include_router(websocket.router, tags=["websocket"])

# Audit log endpoints
app.include_router(audit.router, prefix="/api/v1/audit", tags=["audit"])


@app.get("/")
async def read_root():
    """Root endpoint."""
    return {"message": "Welcome to TaskFlow API!", "version": "1.0.0"}
