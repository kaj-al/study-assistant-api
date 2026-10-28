from fastapi import APIRouter, HTTPException
from schemas import StudyPlan, StudyPlanResponse, TextIn
from services import llm_service

router = APIRouter(prefix="/study", tags=["Study Planner"])

@router.post("/plan", response_model=StudyPlanResponse)
def create_study_plan(data: StudyPlan):
    """Generates a day-by-day personalized study schedule and roadmap."""
    if not data.topic or not data.topic.strip():
        raise HTTPException(status_code=400, detail="Topic is required")

    days = max(1, min(data.days, 60))
    plan_text = llm_service.generate_study_plan(data.topic, days=days, level=data.level or "Intermediate")
    return {
        "topic": data.topic,
        "days": days,
        "level": data.level or "Intermediate",
        "plan": plan_text
    }

@router.post("/from-text")
def study_plan_from_text(data: TextIn):
    """Creates a study roadmap directly from pasted notes, syllabus, or lecture transcripts."""
    if not data.text or not data.text.strip():
        raise HTTPException(status_code=400, detail="Text content is required")

    prompt = (
        "Create an actionable study schedule and 5 practice questions from the following lecture content:\n\n"
        f"{data.text[:6000]}"
    )
    plan_text = llm_service.generate_text(
        prompt,
        system="You are an expert study planner and curriculum architect.",
        max_tokens=2000
    )
    return {"plan": plan_text}
