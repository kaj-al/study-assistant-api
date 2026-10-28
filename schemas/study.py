from pydantic import BaseModel
from typing import Optional, Any

class StudyPlan(BaseModel):
    topic: str
    days: int = 7
    level: Optional[str] = "Intermediate"

class StudyPlanResponse(BaseModel):
    topic: str
    days: int
    level: str
    plan: str

class StudyPlanOut(BaseModel):
    id: int
    topic: str
    days: int
    level: str
    plan: str
    status: str = "active"
    user_email: Optional[str] = ""
    created_at: Optional[Any] = None

class StudyPlanUpdate(BaseModel):
    status: Optional[str] = None
    plan: Optional[str] = None
