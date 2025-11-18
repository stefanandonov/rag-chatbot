from datetime import datetime
from sqlmodel import SQLModel, Field


class Message(SQLModel, table=True):
    """
    Conversation message stored in Postgres.
    """
    id: int | None = Field(default=None, primary_key=True)
    user_id: str
    session_id: str
    role: str                        # "user" or "assistant"
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
