from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List, Dict, Any

from database import get_db
from models import Note, History, QuizAttempt, Quiz, StudyPlan, ChatSession, MediaTranscript, User
from schemas import DashboardStats
from authen import get_current_user_email

router = APIRouter(prefix="/analytics", tags=["Analytics & History"])

@router.get("/stats", response_model=DashboardStats)
def get_user_stats(user_email: Optional[str] = Depends(get_current_user_email), db: Session = Depends(get_db)):
    """Computes real, live study statistics aggregated across the current user's database activities."""
    email_str = (user_email or "").strip().lower()
    is_guest = not email_str or email_str in ["guest@nexora.ai", "guest"]

    user = None
    if not is_guest:
        user = db.query(User).filter(func.lower(User.email) == email_str).first()

    def apply_user_filter(query, model):
        if is_guest:
            return query.filter(model.user_email.in_(["guest@nexora.ai", "guest"]))
        if user and hasattr(model, "user_id"):
            return query.filter(
                (func.lower(model.user_email) == email_str) | (model.user_id == user.id)
            )
        return query.filter(func.lower(model.user_email) == email_str)

    def count_items(model):
        return apply_user_filter(db.query(func.count(model.id)), model).scalar() or 0

    notes_count = count_items(Note)
    quiz_attempts_count = count_items(QuizAttempt)
    quizzes_count = count_items(Quiz)
    study_plans_count = count_items(StudyPlan)
    media_count = count_items(MediaTranscript)
    history_count = count_items(History)

    total_quizzes = quiz_attempts_count if quiz_attempts_count > 0 else quizzes_count

    # Compute realistic study hours based strictly on the user's logged activity:
    calculated_hours = (
        (notes_count * 0.5) +
        (quiz_attempts_count * 0.4) +
        (study_plans_count * 1.0) +
        (media_count * 0.75) +
        (history_count * 0.2)
    )
    study_hours = round(calculated_hours, 1)

    # Compute mastery score: based on actual average score if attempts exist, else based on user activity
    avg_score_query = apply_user_filter(
        db.query(func.avg(QuizAttempt.score_percentage)),
        QuizAttempt
    )
    avg_score = avg_score_query.scalar()

    if avg_score is not None:
        mastery_val = min(100, max(0, int(round(avg_score))))
        mastery = f"{mastery_val}%"
    elif notes_count > 0 or history_count > 0:
        mastery_val = min(100, (notes_count * 10) + (history_count * 5))
        mastery = f"{mastery_val}%"
    else:
        mastery = "0%"

    return {
        "total_notes": notes_count,
        "total_quizzes": total_quizzes,
        "study_hours": study_hours,
        "mastery_score": mastery
    }

@router.get("/history")
def get_user_history(user_email: Optional[str] = Depends(get_current_user_email), db: Session = Depends(get_db)):
    """Retrieves recent learning history across all platform activities."""
    email_str = user_email or "guest@nexora.ai"
    email_filters = [email_str, "guest@nexora.ai", "guest", "student@nexora.ai"]

    items = db.query(History).filter(
        History.user_email.in_(email_filters)
    ).order_by(History.created_at.desc()).limit(30).all()

    return [
        {
            "id": h.id,
            "item_type": h.item_type,
            "title": h.title or h.item_type.capitalize(),
            "org_text": h.org_text,
            "summary": h.summary,
            "created_at": h.created_at
        }
        for h in items
    ]
