from pydantic import BaseModel

class DashboardStats(BaseModel):
    total_notes: int
    total_quizzes: int
    study_hours: float
    mastery_score: str
