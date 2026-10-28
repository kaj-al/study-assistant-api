from fastapi import APIRouter, HTTPException
from schemas import ChatRequest, ChatResponse
from services import llm_service

router = APIRouter(prefix="/chat", tags=["AI Learning Coach & Tutor"])

@router.post("", response_model=ChatResponse)
def chat_with_tutor(data: ChatRequest):
    """
    AI Learning Coach (reflecting tab5.py):
    Explains concepts simply, asks checking questions, adapts to user's answers,
    and supports multi-turn dialogue with memory.
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

    return {
        "reply": reply,
        "action_type": action_type
    }
