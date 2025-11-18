from typing import List
from sqlmodel import select

from backend.models import Message
from backend.db import get_session


def save_message(user_id: str, session_id: str, role: str, content: str):
    """
    Save a single conversation message in the database.
    """
    msg = Message(
        user_id=user_id,
        session_id=session_id,
        role=role,
        content=content,
    )

    with get_session() as session:
        session.add(msg)
        session.commit()


def get_sessions_for_user(user_id: str) -> List[str]:
    """
    Return a list of all distinct session IDs for a given user.
    """
    with get_session() as session:
        result = session.exec(
            select(Message.session_id)
            .where(Message.user_id == user_id)
        ).all()

    # Unique + preserve order
    seen = []
    for s in result:
        if s not in seen:
            seen.append(s)

    return seen


def get_conversation(user_id: str, session_id: str, limit: int = 50):
    """
    Return conversation messages for a given user + session.
    Ordered oldest → newest.
    """
    with get_session() as session:
        result = session.exec(
            select(Message)
            .where(
                (Message.user_id == user_id) &
                (Message.session_id == session_id)
            )
            .order_by(Message.created_at)
            .limit(limit)
        ).all()

    # Convert ORM objects → simple dicts for Streamlit & LLM
    return [
        {"role": m.role, "content": m.content}
        for m in result
    ]
