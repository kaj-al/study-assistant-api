from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional, List

from database import get_db
from models import ChatSession as ChatSessionModel, ChatMessage as ChatMessageModel, User, History
from schemas import (
    ChatRequest,
    ChatResponse,
    ChatSessionOut,
    ChatMessageOut
)
from authen import security, get_current_user_email
from services import llm_service

router = APIRouter(prefix="/chat", tags=["AI Learning Coach & Tutor"])

@router.post("", response_model=ChatResponse)
def chat_with_tutor(
    data: ChatRequest,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """
    AI Learning Coach (reflecting tab5.py):
    Explains concepts simply, asks checking questions, adapts to user's answers,
    supports multi-turn dialogue with memory, and automatically logs conversation to database.
    """
    if not data.message or not data.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    history_dicts = [{"role": m.role, "content": m.content} for m in (data.history or [])]
    reply = llm_service.tutor_chat_coach(
        user_message=data.message.strip(),
        history=history_dicts,
        language=data.language or "English"
    )

    action_type = "explanation"
    if "?" in reply:
        action_type = "question"
    if any(w in reply.lower() for w in ["correct", "great job", "well done", "incorrect", "almost"]):
        action_type = "feedback"

    user_email = get_current_user_email(credentials) or "guest@nexora.ai"
    user = db.query(User).filter(User.email == user_email).first()
    user_id = user.id if user else None

    # Persist chat session & messages
    try:
        # Find active session or create new one
        session = db.query(ChatSessionModel).filter(
            ChatSessionModel.user_email == user_email
        ).order_by(ChatSessionModel.updated_at.desc()).first()

        if not session:
            title_text = data.message[:40] + ("..." if len(data.message) > 40 else "")
            session = ChatSessionModel(
                user_id=user_id,
                user_email=user_email,
                title=title_text,
                language=data.language or "English"
            )
            db.add(session)
            db.flush()

        # Add user message
        user_msg = ChatMessageModel(
            session_id=session.id,
            user_email=user_email,
            role="user",
            content=data.message.strip(),
            action_type="user_query"
        )
        db.add(user_msg)

        # Add assistant message
        tutor_msg = ChatMessageModel(
            session_id=session.id,
            user_email=user_email,
            role="assistant",
            content=reply,
            action_type=action_type
        )
        db.add(tutor_msg)

        db.commit()
    except Exception:
        db.rollback()

    return {
        "reply": reply,
        "action_type": action_type
    }

@router.get("/sessions", response_model=List[ChatSessionOut])
def get_user_chat_sessions(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Retrieves all chat conversation threads for the user."""
    user_email = get_current_user_email(credentials) or "guest@nexora.ai"
    sessions = db.query(ChatSessionModel).filter(
        (ChatSessionModel.user_email == user_email) | (ChatSessionModel.user_email == "guest@nexora.ai")
    ).order_by(ChatSessionModel.updated_at.desc()).all()

    return [
        {
            "id": s.id,
            "title": s.title,
            "language": s.language,
            "user_email": s.user_email,
            "created_at": s.created_at,
            "updated_at": s.updated_at,
            "message_count": len(s.messages)
        }
        for s in sessions
    ]

@router.get("/sessions/{session_id}", response_model=List[ChatMessageOut])
def get_session_messages(
    session_id: int,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Retrieves message history for a specific conversation session."""
    session = db.query(ChatSessionModel).filter(ChatSessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    messages = db.query(ChatMessageModel).filter(
        ChatMessageModel.session_id == session_id
    ).order_by(ChatMessageModel.created_at.asc()).all()

    return [
        {
            "id": m.id,
            "session_id": m.session_id,
            "role": m.role,
            "content": m.content,
            "action_type": m.action_type,
            "created_at": m.created_at
        }
        for m in messages
    ]

@router.delete("/sessions/{session_id}")
def delete_chat_session(
    session_id: int,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Deletes a chat session and all its messages."""
    session = db.query(ChatSessionModel).filter(ChatSessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    db.delete(session)
    db.commit()
    return {"message": "Chat session deleted successfully", "id": session_id}
