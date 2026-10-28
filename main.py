import os
import sys
import logging

# Ensure local modules (database, models, routers, services) resolve regardless of CWD or package root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware

from database import engine, Base, SessionLocal
import models

# Import modular routers
from routers.auth import router as auth_router
from routers.media import router as media_router
from routers.study import router as study_router
from routers.assessment import router as assessment_router
from routers.recommendations import router as recommendations_router
from routers.chat import router as chat_router
from routers.notes import router as notes_router
from routers.analytics import router as analytics_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create database tables automatically
Base.metadata.create_all(bind=engine)

def seed_initial_data():
    from models import User, Note
    from authen import hashPassword
    db = SessionLocal()
    try:
        demo_user = db.query(User).filter(User.email == "student@nexora.ai").first()
        if not demo_user:
            demo_user = User(
                name="Nexora Student",
                email="student@nexora.ai",
                password=hashPassword("nexoraPassword123")
            )
            db.add(demo_user)
            db.commit()
            db.refresh(demo_user)

        user_notes = db.query(Note).filter((Note.user_email == "student@nexora.ai") | (Note.user_email == "guest")).count()
        if user_notes == 0:
            sample_notes = [
                Note(
                    title="Cell Biology: Photosynthesis & Light Reactions",
                    content="Photosynthesis converts solar light energy into chemical energy stored in glucose. Light-dependent reactions generate ATP and NADPH in the thylakoid membranes, while the Calvin Cycle fixes CO2 into glyceraldehyde 3-phosphate.",
                    summary="Light reactions produce ATP & NADPH; the Calvin cycle uses them to synthesize glucose from CO2.",
                    tags="Biology",
                    user_email="student@nexora.ai"
                ),
                Note(
                    title="Physics: Newton's Laws & Dynamics",
                    content="First Law: Inertia. Second Law: F = ma. Third Law: For every action, there is an equal and opposite reaction. Momentum is conserved in isolated systems.",
                    summary="Newton's laws describe the relationship between an object's motion and the net forces acting upon it.",
                    tags="Physics",
                    user_email="student@nexora.ai"
                ),
                Note(
                    title="Computer Science: Asymptotic Analysis & Big-O",
                    content="Big-O notation describes the upper bound of an algorithm's runtime or space requirements as input size n grows to infinity. Key classes: O(1), O(log n), O(n), O(n log n), O(n^2).",
                    summary="Big-O classifies algorithm scalability and performance worst-case guarantees.",
                    tags="Computer Science",
                    user_email="student@nexora.ai"
                )
            ]
            db.add_all(sample_notes)
            db.commit()
    except Exception as e:
        logger.warning(f"Seed initial data note: {e}")
        db.rollback()
    finally:
        db.close()

seed_initial_data()

app = FastAPI(
    title="Nexora AI Study Platform API",
    description="Unified API Engine powering Audio Notes, Study Planning, Quizzes, AI Tutor Chat, and Smart Learning Recommendations",
    version="2.5.0"
)

# Enable CORS for Next.js frontend and external clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all modular routers
app.include_router(auth_router)
app.include_router(media_router)
app.include_router(study_router)
app.include_router(assessment_router)
app.include_router(recommendations_router)
app.include_router(chat_router)
app.include_router(notes_router)
app.include_router(analytics_router)

# ----------------- Root & Health Endpoints -----------------

@app.get("/")
def root():
    return {
        "status": "online",
        "service": "Nexora AI Study Platform API",
        "version": "2.5.0",
        "documentation": "/docs",
        "modules": [
            "Authentication (/auth)",
            "Audio & Video Notes (/media)",
            "Study Roadmaps (/study)",
            "Assessment & Quizzes (/assessment)",
            "Smart Recommendations (/recommendations)",
            "AI Learning Coach (/chat)",
            "Notebook & Summaries (/notes)",
            "Analytics (/analytics)"
        ]
    }

@app.get("/health")
def health():
    db_type = "postgresql" if "postgres" in os.getenv("DATABASE_URL", "") else "sqlite"
    return {
        "status": "healthy",
        "database": db_type,
        "service": "nexora-backend",
        "version": "2.5.0"
    }

# ----------------- Backward Compatibility Top-Level Routes -----------------
# Ensures frontend calls matching root paths work interchangeably

from typing import Optional
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database import SessionLocal
from authen import security, get_current_user, get_current_user_email
from schemas import (
    Signup, Login, Notes, StudyPlan, QuizRequest,
    AssessmentRequest, ChatRequest, NoteCreate
)
from routers.auth import signup as auth_signup, login as auth_login, get_me as auth_me
from routers.notes import summarize as notes_summarize, get_user_notes, save_note as notes_save, delete_note as notes_del
from routers.assessment import generate_quiz as assess_quiz, generate_assessment_paper as assess_gen
from routers.study import create_study_plan as study_gen
from routers.chat import chat_with_tutor as chat_gen
from routers.analytics import get_user_stats as stats_gen, get_user_history as hist_gen

def get_root_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/signup")
def root_signup(data: Signup, db: Session = Depends(get_root_db)):
    return auth_signup(data, db)

@app.post("/login")
def root_login(data: Login, db: Session = Depends(get_root_db)):
    return auth_login(data, db)

@app.get("/me")
def root_me(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    return auth_me(get_current_user(credentials))

@app.post("/summarize")
def root_summarize(data: Notes, credentials: Optional[HTTPAuthorizationCredentials] = Depends(security), db: Session = Depends(get_root_db)):
    user_email = get_current_user_email(credentials)
    return notes_summarize(data, user_email, db)

@app.post("/quiz")
def root_quiz(data: QuizRequest):
    return assess_quiz(data)

@app.post("/study-plan")
def root_study_plan(data: StudyPlan):
    return study_gen(data)

@app.post("/assessment")
def root_assessment(data: AssessmentRequest):
    return assess_gen(data)

@app.get("/stats")
def root_stats(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security), db: Session = Depends(get_root_db)):
    user_email = get_current_user_email(credentials)
    return stats_gen(user_email, db)

@app.get("/history")
def root_history(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security), db: Session = Depends(get_root_db)):
    user_email = get_current_user_email(credentials)
    return hist_gen(user_email, db)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
