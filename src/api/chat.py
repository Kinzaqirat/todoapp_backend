"""API routes for chatbot."""

from fastapi import APIRouter
from ..schemas.chat import ChatRequest, ChatResponse, ChatMessage
from ..services.chatbot import chat_with_assistant

router = APIRouter()


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process a chat message and return AI response.

    The chatbot can:
    - Add new tasks
    - Delete tasks
    - Update tasks
    - List tasks (with filtering and sorting)
    - Mark tasks as complete
    - Search tasks
    """
    # Convert conversation history to dict format
    history = None
    if request.conversation_history:
        
        history = [{"role": msg.role, "content": msg.content} for msg in request.conversation_history]

    # Get response from chatbot
    response_message, action_taken, task_data = chat_with_assistant(
        message=request.message,
        conversation_history=history
    )

    return ChatResponse(
        response=response_message,
        action_taken=action_taken,
        task_data=task_data
    )


@router.get("/health")
async def chat_health():
    """Health check for chat service."""
    return {"status": "ok", "service": "chatbot"}
