from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional, List

from database import get_db
from models import StudyPlan as StudyPlanModel, User, History
from schemas import (
    StudyPlan,
    StudyPlanResponse,
    TextIn,
    StudyPlanOut,
    StudyPlanUpdate
)
from authen import security, get_current_user_email
from services import llm_service

router = APIRouter(prefix="/study", tags=["Study Planner"])

@router.post("/plan", response_model=StudyPlanResponse)
def create_study_plan(
    data: StudyPlan,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Generates a day-by-day personalized study schedule and roadmap, persisting it to the database."""
    if not data.topic or not data.topic.strip():
        raise HTTPException(status_code=400, detail="Topic is required")

    user_email = get_current_user_email(credentials) or "guest@nexora.ai"
    user = db.query(User).filter(User.email == user_email).first()
    user_id = user.id if user else None

    days = max(1, min(data.days, 60))
    level = data.level or "Intermediate"
    plan_text = llm_service.generate_study_plan(data.topic, days=days, level=level)

    try:
        new_plan = StudyPlanModel(
            user_id=user_id,
            user_email=user_email,
            topic=data.topic.strip(),
            days=days,
            level=level,
            plan_text=plan_text,
            status="active"
        )
        db.add(new_plan)

        hist = History(
            user_id=user_id,
            user_email=user_email,
            item_type="study_plan",
            title=f"Study Plan: {data.topic.strip()}",
            org_text=f"Topic: {data.topic}, Days: {days}, Level: {level}",
            summary=plan_text[:400]
        )
        db.add(hist)
        db.commit()
    except Exception:
        db.rollback()

    return {
        "topic": data.topic,
        "days": days,
        "level": level,
        "plan": plan_text
    }

@router.post("/from-text")
def study_plan_from_text(
    data: TextIn,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Creates a study roadmap directly from pasted notes, syllabus, or lecture transcripts."""
    if not data.text or not data.text.strip():
        raise HTTPException(status_code=400, detail="Text content is required")

    user_email = get_current_user_email(credentials) or "guest@nexora.ai"
    user = db.query(User).filter(User.email == user_email).first()
    user_id = user.id if user else None

    prompt = (
        "Create an actionable study schedule and 5 practice questions from the following lecture content:\n\n"
        f"{data.text[:6000]}"
    )
    plan_text = llm_service.generate_text(
        prompt,
        system="You are an expert study planner and curriculum architect.",
        max_tokens=2000
    )

    try:
        new_plan = StudyPlanModel(
            user_id=user_id,
            user_email=user_email,
            topic="Custom Material Roadmap",
            days=7,
            level="Intermediate",
            plan_text=plan_text,
            status="active"
        )
        db.add(new_plan)

        hist = History(
            user_id=user_id,
            user_email=user_email,
            item_type="study_plan",
            title="Custom Material Roadmap",
            org_text=data.text[:500],
            summary=plan_text[:400]
        )
        db.add(hist)
        db.commit()
    except Exception:
        db.rollback()

    return {"plan": plan_text}

@router.get("/plans", response_model=List[StudyPlanOut])
def get_user_study_plans(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Retrieves all saved study plans for the current user."""
    user_email = get_current_user_email(credentials) or "guest@nexora.ai"
    plans = db.query(StudyPlanModel).filter(
        (StudyPlanModel.user_email == user_email) | (StudyPlanModel.user_email == "guest@nexora.ai")
    ).order_by(StudyPlanModel.created_at.desc()).all()

    return [
        {
            "id": p.id,
            "topic": p.topic,
            "days": p.days,
            "level": p.level,
            "plan": p.plan_text,
            "status": p.status,
            "user_email": p.user_email,
            "created_at": p.created_at
        }
        for p in plans
    ]

@router.get("/plans/{plan_id}", response_model=StudyPlanOut)
def get_study_plan_by_id(
    plan_id: int,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Retrieves a single study plan by ID."""
    plan = db.query(StudyPlanModel).filter(StudyPlanModel.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Study plan not found")
    return {
        "id": plan.id,
        "topic": plan.topic,
        "days": plan.days,
        "level": plan.level,
        "plan": plan.plan_text,
        "status": plan.status,
        "user_email": plan.user_email,
        "created_at": plan.created_at
    }

@router.patch("/plans/{plan_id}", response_model=StudyPlanOut)
def update_study_plan(
    plan_id: int,
    data: StudyPlanUpdate,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Updates a study plan's status (active, completed, archived) or content."""
    plan = db.query(StudyPlanModel).filter(StudyPlanModel.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Study plan not found")

    if data.status:
        plan.status = data.status
    if data.plan:
        plan.plan_text = data.plan

    db.commit()
    db.refresh(plan)
    return {
        "id": plan.id,
        "topic": plan.topic,
        "days": plan.days,
        "level": plan.level,
        "plan": plan.plan_text,
        "status": plan.status,
        "user_email": plan.user_email,
        "created_at": plan.created_at
    }

@router.delete("/plans/{plan_id}")
def delete_study_plan(
    plan_id: int,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Deletes a study plan from the database."""
    plan = db.query(StudyPlanModel).filter(StudyPlanModel.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Study plan not found")

    db.delete(plan)
    db.commit()
    return {"message": "Study plan deleted successfully", "id": plan_id}
