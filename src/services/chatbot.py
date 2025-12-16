# 










"""Chatbot service using OpenAI SDK with Gemini API."""

import os
import json
from typing import Optional, List
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

# Load environment variables
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent.parent / ".env" 
load_dotenv(dotenv_path=env_path)

# --- IMPORTS for Core Logic ---
try:
    from openai import OpenAI
    from ..crud import TaskStorage 
    from ..models import Priority, Task
except ImportError as e:
    print(f"IMPORT ERROR ON STARTUP: {e}")
    raise e 

# --- API CLIENT INITIALIZATION ---
client = OpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

# Initialize task storage
task_storage = TaskStorage()

# --- FastAPI Setup ---
router = APIRouter()

# --- Pydantic Schemas ---
class ChatMessage(BaseModel):
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")

class ChatRequest(BaseModel):
    message: str = Field(..., description="The user's new chat message.")
    conversation_history: Optional[List[ChatMessage]] = Field(None, description="Previous messages in the conversation.")

class ChatResponse(BaseModel):
    response_message: str = Field(..., description="The assistant's text response.")
    action_taken: Optional[str] = Field(None, description="The action the assistant decided to take.")
    task_data: Optional[dict] = Field(None, description="Data related to the task action.")


# --- SYSTEM PROMPT ---
SYSTEM_PROMPT = """You are a helpful task management assistant. You help users manage their todo tasks.

When users want to perform task operations, respond with JSON in this format:
{
    "action": "ADD|DELETE|UPDATE|COMPLETE|LIST|SEARCH",
    "params": {...relevant parameters...},
    "message": "A friendly message to the user"
}

For ADD tasks, use these parameters:
- title (required)
- description (optional)
- priority: "high", "medium", or "low"
- tags: array of strings
- due_date: ISO format date string
- recurrence: "daily", "weekly", or "monthly"

For other actions:
- DELETE/UPDATE/COMPLETE: Include "task_id"
- SEARCH: Include "query"
- LIST: Include optional "filter" (completed/pending/all)

Always be helpful and confirm actions after completing them.
"""

def parse_ai_response(response_text: str) -> tuple[Optional[dict], str]:
    """Parse AI response to extract action and message."""
    try:
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            json_str = response_text[json_start:json_end].strip()
            action_data = json.loads(json_str)
            return action_data, action_data.get("message", "")

        if response_text.strip().startswith("{"):
            action_data = json.loads(response_text)
            return action_data, action_data.get("message", "")
    except json.JSONDecodeError:
        pass
    return None, response_text


def execute_task_action(action_data: dict) -> tuple[str, Optional[dict]]:
    """Execute a task action based on parsed AI response."""
    action = action_data.get("action", "").upper()
    params = action_data.get("params", {})
    
    if action == "ADD":
        title = params.get("title")
        if not title:
            return "I need a title to create a task.", None
        
        priority = None
        if params.get("priority"):
            priority_map = {"high": Priority.HIGH, "medium": Priority.MEDIUM, "low": Priority.LOW}
            priority = priority_map.get(params["priority"].lower())

        due_date = None
        if params.get("due_date"):
            try:
                due_date = datetime.fromisoformat(params["due_date"].replace("Z", "+00:00"))
            except ValueError:
                pass

        task = task_storage.add_task(
            title=title,
            description=params.get("description", ""),
            priority=priority,
            tags=params.get("tags", []),
            due_date=due_date,
            recurrence=params.get("recurrence")
        )
        return f"Task '{task.title}' created successfully with ID {task.id}!", task.model_dump(mode='json')
    
    elif action == "LIST":
        tasks = task_storage.get_all_tasks()
        if not tasks:
            return "You have no tasks.", {"tasks": []}

        task_summary = "\n".join([
             f"- [{t.id}] {t.title} {'✓' if t.completed else '○'}"
             for t in tasks
         ])
        return f"Here are your tasks:\n{task_summary}", {"tasks": [t.model_dump(mode='json') for t in tasks]}
    
    elif action == "DELETE":
        task_id = params.get("task_id")
        if not task_id:
            return "I need a task ID to delete.", None
        
        success = task_storage.delete_task(task_id)
        if success:
            return f"Task {task_id} deleted successfully!", None
        return f"Could not find task {task_id}.", None
    
    elif action == "COMPLETE":
        task_id = params.get("task_id")
        if not task_id:
            return "I need a task ID to mark as complete.", None
        
        task = task_storage.complete_task(task_id)
        if task:
            return f"Task '{task.title}' marked as complete!", task.model_dump(mode='json')
        return f"Could not find task {task_id}.", None
    
    elif action == "UPDATE":
        task_id = params.get("task_id")
        if not task_id:
            return "I need a task ID to update.", None
        
        task = task_storage.update_task(task_id, **params)
        if task:
            return f"Task '{task.title}' updated successfully!", task.model_dump(mode='json')
        return f"Could not find task {task_id}.", None
    
    elif action == "SEARCH":
        query = params.get("query", "")
        tasks = task_storage.search_tasks(query)
        if not tasks:
            return f"No tasks found matching '{query}'.", {"tasks": []}
        
        task_summary = "\n".join([
             f"- [{t.id}] {t.title} {'✓' if t.completed else '○'}"
             for t in tasks
         ])
        return f"Found {len(tasks)} task(s):\n{task_summary}", {"tasks": [t.model_dump(mode='json') for t in tasks]}
    
    return "I'm not sure what action to take.", None


def chat_with_assistant(
    message: str,
    conversation_history: Optional[List[ChatMessage]] = None
) -> tuple[str, Optional[str], Optional[dict]]:
    """Process a chat message and return response."""
    # Build messages for the API
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Add current tasks context
    current_tasks = task_storage.get_all_tasks()
    if current_tasks:
        tasks_context = "Current tasks:\n" + "\n".join([
            f"- ID: {t.id}, Title: {t.title}, Completed: {t.completed}"
            for t in current_tasks
        ])
        messages.append({"role": "system", "content": tasks_context})

    # Add conversation history with validation
    if conversation_history:
        for msg in conversation_history:
            # Validate role and content
            if isinstance(msg, ChatMessage):
                role = msg.role
                content = msg.content
            elif isinstance(msg, dict):
                role = msg.get("role")
                content = msg.get("content")
            else:
                continue  # Skip invalid messages
            
            # Only add valid roles
            if role in ["user", "assistant"] and content:
                messages.append({"role": role, "content": str(content)})
    
    # Add current user message
    messages.append({"role": "user", "content": message})

    try:
        # Call Gemini API via OpenAI SDK
        response = client.chat.completions.create(
            model="gemini-2.5-flash",
            messages=messages,
            temperature=0.7,
            max_tokens=1024
        )

        ai_response = response.choices[0].message.content
        action_data, response_message = parse_ai_response(ai_response)

        if action_data and action_data.get("action"):
            result_message, task_data = execute_task_action(action_data)
            action_taken = action_data.get("action")
            final_message = action_data.get("message", "") + "\n\n" + result_message
            return final_message.strip(), action_taken, task_data

        return response_message, None, None

    except Exception as e:
        return f"Sorry, I encountered an error: {str(e)}", None, None


@router.post("/process", response_model=ChatResponse)
async def process_chat(request: ChatRequest):
    """
    Process a user's chat message using the Gemini assistant.
    """
    response_message, action_taken, task_data = chat_with_assistant(
        message=request.message,
        conversation_history=request.conversation_history
    )
    
    return ChatResponse(
        response_message=response_message,
        action_taken=action_taken,
        task_data=task_data
    )