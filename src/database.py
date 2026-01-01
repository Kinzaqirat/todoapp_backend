"""Database configuration for TaskFlow.

This module provides the database engine and table creation.
Use db.session.get_session() for database sessions.
"""

from sqlmodel import SQLModel, create_engine
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./database.db")

# Import models so they're registered with SQLModel.metadata
from models.user import User
from models.task import Task
from models.conversation import Conversation

engine = create_engine(DATABASE_URL, echo=True)


def create_db_and_tables():
    """Create all database tables."""
    SQLModel.metadata.create_all(engine)


# Re-export from db.session for backwards compatibility
from db.session import get_session