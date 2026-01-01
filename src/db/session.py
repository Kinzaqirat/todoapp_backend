"""Database session management for TaskFlow."""

from sqlmodel import Session, create_engine
from typing import Generator
import os


def get_engine():
    """Create and return database engine using DATABASE_URL from environment."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")
    return create_engine(database_url)


engine = get_engine()


def get_session() -> Generator[Session, None, None]:
    """Get a database session.

    Yields:
        Session: Database session

    Usage:
        with get_session() as session:
            session.add(task)
            session.commit()
    """
    with Session(engine) as session:
        yield session
