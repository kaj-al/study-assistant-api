from pydantic import BaseModel
from typing import Optional, List, Any

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = []
    language: Optional[str] = "English"

class ChatResponse(BaseModel):
    reply: str
    action_type: Optional[str] = "explanation"  # "explanation", "question", "feedback"

class ChatSessionOut(BaseModel):
    id: int
    title: str
    language: str
    user_email: Optional[str] = ""
    created_at: Optional[Any] = None
    updated_at: Optional[Any] = None
    message_count: Optional[int] = 0

class ChatMessageOut(BaseModel):
    id: int
    session_id: Optional[int] = None
    role: str
    content: str
    action_type: Optional[str] = "explanation"
    created_at: Optional[Any] = None
