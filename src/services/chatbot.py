# 










"""Chatbot service using OpenAI SDK with Gemini API."""

import os
import json
from typing import Optional, List
from datetime import datetime
from pathlib import Path
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

# --- API CLIENT INITIALIZATION (Lazy) ---
_client = None

def get_client():
    """Lazily initialize the OpenAI client."""
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set")
        _client = OpenAI(
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
    return _client

# Initialize task storage
task_storage = TaskStorage()

# --- Import Pydantic Schemas from shared location ---
from ..schemas.chat import ChatMessage, ChatRequest, ChatResponse


# --- PRIORITY INFERENCE RULES ---
PRIORITY_HIGH_KEYWORDS = ["urgent", "asap", "important", "critical", "immediately", "right now", "emergency"]
PRIORITY_LOW_KEYWORDS = ["whenever", "someday", "low priority", "not urgent", "when you can", "no rush", "eventually"]

# --- TAG EXTRACTION RULES ---
TAG_MAPPINGS = {
    "work": ["work", "office", "job", "meeting", "report", "project", "deadline", "colleague", "boss"],
    "personal": ["home", "personal", "family", "friend", "myself"],
    "shopping": ["shopping", "groceries", "buy", "purchase", "store", "market"],
    "health": ["health", "doctor", "gym", "exercise", "workout", "medicine", "appointment", "dentist"],
}


def infer_priority(text: str) -> str:
    """Infer priority from text keywords."""
    text_lower = text.lower()
    for keyword in PRIORITY_HIGH_KEYWORDS:
        if keyword in text_lower:
            return "high"
    for keyword in PRIORITY_LOW_KEYWORDS:
        if keyword in text_lower:
            return "low"
    return "medium"




def extract_tags(text: str) -> list[str]:
    """Extract tags from text based on keyword mappings."""
    text_lower = text.lower()
    tags = []

    # Check for explicit hashtags
    import re
    explicit_tags = re.findall(r'#(\w+)', text)
    tags.extend(explicit_tags)

    # Check for keyword-based tags
    for tag, keywords in TAG_MAPPINGS.items():
        for keyword in keywords:
            if keyword in text_lower and tag not in tags:
                tags.append(tag)
                break

    return tags


def check_duplicate_task(title: str, existing_tasks: list) -> Optional[str]:
    """Check if a similar task already exists."""
    title_lower = title.lower()
    for task in existing_tasks:
        if task.title.lower() == title_lower:
            return task.title
        # Fuzzy match - if title contains 80% of the words
        title_words = set(title_lower.split())
        task_words = set(task.title.lower().split())
        if title_words and task_words:
            overlap = len(title_words & task_words) / max(len(title_words), len(task_words))
            if overlap > 0.7:
                return task.title
    return None


# --- SYSTEM PROMPT ---
SYSTEM_PROMPT = """You are a helpful task management assistant. You help users manage their todo tasks.

When users want to perform task operations, respond with JSON in this format:
{
    "action": "ADD|DELETE|UPDATE|COMPLETE|LIST|SEARCH|CLARIFY",
    "params": {...relevant parameters...},
    "message": "A friendly message to the user"
}

For ADD tasks, use these parameters:
- title (required)
- description (optional)
- priority: "high", "medium", or "low" (infer from context: "urgent/asap/critical" = high, "whenever/someday" = low)
- tags: array of strings (infer from context: "work/office" = work, "home/personal" = personal, "buy/groceries" = shopping, "gym/doctor" = health)
- due_date: ISO format date string (e.g., "2025-12-30T09:00:00")

For other actions:
- DELETE/UPDATE/COMPLETE: Include "task_id" (the numeric ID)
- SEARCH: Include "query"
- LIST: Include optional "filter" (completed/pending/all), "priority", "tag", "sort_by" (priority/due-date/title)

For CLARIFY (when input is ambiguous):
- question: The clarifying question to ask the user

Priority Inference Rules:
- Words like "urgent", "asap", "important", "critical" → priority: "high"
- Words like "whenever", "someday", "low priority", "no rush" → priority: "low"
- Default → priority: "medium"

Tag Extraction Rules:
- "work", "office", "job", "meeting" → tag: "work"
- "home", "personal", "family" → tag: "personal"
- "shopping", "groceries", "buy" → tag: "shopping"
- "health", "doctor", "gym", "exercise" → tag: "health"
- Explicit #hashtags should be preserved as-is

When the user's request is ambiguous (like "remind me about that thing"), use CLARIFY action to ask for more details.

Proactive Behavior:
- If there are overdue tasks or high-priority tasks, mention them when relevant
- When a user completes all tasks, congratulate them
- Provide helpful summaries when asked about task status

Always be helpful, conversational, and confirm actions after completing them.
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


def execute_task_action(action_data: dict, original_message: str = "") -> tuple[str, Optional[dict]]:
    """Execute a task action based on parsed AI response."""
    action = action_data.get("action", "").upper()
    params = action_data.get("params", {})

    if action == "CLARIFY":
        question = params.get("question", action_data.get("message", "Could you please provide more details?"))
        return question, {"action": "clarify", "question": question}

    if action == "ADD":
        title = params.get("title")
        if not title:
            return "I need a title to create a task.", None

        # Check for duplicate tasks
        existing_tasks = task_storage.get_all_tasks()
        duplicate = check_duplicate_task(title, existing_tasks)
        if duplicate:
            return f"You already have a similar task: '{duplicate}'. Would you still like to create this task?", {
                "action": "duplicate_warning",
                "existing_title": duplicate,
                "new_title": title
            }

        # Infer priority from original message if not explicitly set
        priority_str = params.get("priority")
        if not priority_str:
            priority_str = infer_priority(original_message)

        priority = None
        if priority_str:
            priority_map = {"high": Priority.HIGH, "medium": Priority.MEDIUM, "low": Priority.LOW}
            priority = priority_map.get(priority_str.lower())

        # Extract tags from original message if not provided
        tags = params.get("tags", [])
        if not tags:
            tags = extract_tags(original_message)

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
            tags=tags,
            due_date=due_date
        )

        # Build confirmation message with inferred attributes
        priority_note = f" with priority '{priority_str}'" if priority_str != "medium" else ""
        tags_note = f" tagged as {', '.join(['#' + t for t in tags])}" if tags else ""
        return f"Task '{task.title}' created successfully (ID: {task.id}){priority_note}{tags_note}!", task.model_dump(mode='json')
    
    elif action == "LIST":
        tasks = task_storage.get_all_tasks()

        # Apply filters
        filter_status = params.get("filter")
        filter_priority = params.get("priority")
        filter_tag = params.get("tag")
        sort_by = params.get("sort_by")

        if filter_status:
            if filter_status == "completed":
                tasks = [t for t in tasks if t.completed]
            elif filter_status == "pending":
                tasks = [t for t in tasks if not t.completed]

        if filter_priority:
            tasks = [t for t in tasks if t.priority and (t.priority.value if hasattr(t.priority, 'value') else t.priority) == filter_priority]

        if filter_tag:
            tag_lower = filter_tag.lower()
            filtered = []
            for t in tasks:
                task_tags = json.loads(t.tags) if isinstance(t.tags, str) else t.tags
                if tag_lower in [tag.lower() for tag in task_tags]:
                    filtered.append(t)
            tasks = filtered

        # Apply sorting
        if sort_by:
            tasks = task_storage.sort_tasks(tasks, sort_by)

        if not tasks:
            filter_desc = []
            if filter_status:
                filter_desc.append(filter_status)
            if filter_priority:
                filter_desc.append(f"{filter_priority} priority")
            if filter_tag:
                filter_desc.append(f"#{filter_tag}")
            filter_msg = f" matching {', '.join(filter_desc)}" if filter_desc else ""
            return f"You have no tasks{filter_msg}.", {"tasks": []}

        task_summary = "\n".join([
            f"- [{t.id}] {t.title} {'✓' if t.completed else '○'}" +
            (f" [{(t.priority.value if hasattr(t.priority, 'value') else t.priority)}]" if t.priority else "") +
            (f" {', '.join(['#' + tag for tag in (json.loads(t.tags) if isinstance(t.tags, str) else t.tags)])}" if t.tags and (json.loads(t.tags) if isinstance(t.tags, str) else t.tags) else "")
            for t in tasks
        ])
        return f"Here are your tasks ({len(tasks)}):\n{task_summary}", {"tasks": [t.model_dump(mode='json') for t in tasks]}
    
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


def get_task_summary() -> dict:
    """Generate a summary of task statistics for contextual suggestions."""
    tasks = task_storage.get_all_tasks()
    today = datetime.now().date()

    summary = {
        "total": len(tasks),
        "pending": sum(1 for t in tasks if not t.completed),
        "completed": sum(1 for t in tasks if t.completed),
        "high_priority": sum(1 for t in tasks if not t.completed and t.priority and (t.priority.value if hasattr(t.priority, 'value') else t.priority) == "high"),
        "due_today": 0,
        "overdue": 0,
    }

    for t in tasks:
        if not t.completed and t.due_date:
            due_date = t.due_date.date() if hasattr(t.due_date, 'date') else t.due_date
            if due_date == today:
                summary["due_today"] += 1
            elif due_date < today:
                summary["overdue"] += 1

    return summary


def generate_proactive_context(summary: dict) -> str:
    """Generate proactive context message based on task summary."""
    alerts = []

    if summary["overdue"] > 0:
        alerts.append(f"⚠️ You have {summary['overdue']} overdue task(s)")

    if summary["due_today"] > 0:
        alerts.append(f"📅 {summary['due_today']} task(s) due today")

    if summary["high_priority"] > 0:
        alerts.append(f"🔴 {summary['high_priority']} high-priority pending task(s)")

    if alerts:
        return "PROACTIVE ALERTS for user:\n" + "\n".join(alerts) + "\n\nMention these alerts naturally in your response when relevant."

    return ""


def chat_with_assistant(
    message: str,
    conversation_history: Optional[List[ChatMessage]] = None
) -> tuple[str, Optional[str], Optional[dict]]:
    """Process a chat message and return response."""
    # Build messages for the API
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Add current tasks context with full details
    current_tasks = task_storage.get_all_tasks()

    # Generate and add proactive context
    summary = get_task_summary()
    proactive_context = generate_proactive_context(summary)
    if proactive_context:
        messages.append({"role": "system", "content": proactive_context})
    if current_tasks:
        def format_task(t):
            parts = [f"ID: {t.id}", f"Title: {t.title}"]
            parts.append(f"Status: {'completed' if t.completed else 'pending'}")
            if t.priority:
                p_val = t.priority.value if hasattr(t.priority, 'value') else t.priority
                parts.append(f"Priority: {p_val}")
            if t.tags:
                task_tags = json.loads(t.tags) if isinstance(t.tags, str) else t.tags
                if task_tags:
                    parts.append(f"Tags: {', '.join(task_tags)}")
            if t.due_date:
                parts.append(f"Due: {t.due_date.strftime('%Y-%m-%d %H:%M')}")
            return "- " + ", ".join(parts)

        tasks_context = f"Current tasks ({len(current_tasks)} total):\n" + "\n".join([
            format_task(t) for t in current_tasks
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
        try:
            client = get_client()
        except Exception as client_error:
            return f"Failed to initialize AI client: {str(client_error)}", None, None

        response = client.chat.completions.create(
            model="gemini-2.5-flash",
            messages=messages,
            temperature=0.7,
            max_tokens=1024
        )

        ai_response = response.choices[0].message.content
        action_data, response_message = parse_ai_response(ai_response)

        if action_data and action_data.get("action"):
            result_message, task_data = execute_task_action(action_data, original_message=message)
            action_taken = action_data.get("action")
            final_message = action_data.get("message", "") + "\n\n" + result_message
            return final_message.strip(), action_taken, task_data

        return response_message, None, None

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Chatbot error: {error_details}")
        return f"Sorry, I encountered an error: {str(e)}", None, None


# Note: The API endpoint is defined in src/api/chat.py
# This service module only contains the business logic