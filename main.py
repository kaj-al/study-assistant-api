import os
import sys
import logging
import json
from typing import Optional

# Ensure local modules (database, models, routers, services) resolve regardless of CWD or package root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from database import engine, Base, SessionLocal, get_db
import models

# Import modular routers
from routers.auth import router as auth_router, signup as auth_signup, login as auth_login, get_me as auth_me
from routers.media import router as media_router
from routers.study import router as study_router, create_study_plan as study_gen
from routers.assessment import router as assessment_router, generate_quiz as assess_quiz, generate_assessment_paper as assess_gen
from routers.recommendations import router as recommendations_router
from routers.chat import router as chat_router, chat_with_tutor as chat_gen
from routers.notes import router as notes_router, summarize as notes_summarize, get_user_notes, save_note as notes_save, delete_note as notes_del
from routers.analytics import router as analytics_router, get_user_stats as stats_gen, get_user_history as hist_gen

from authen import security, get_current_user_email
from schemas import (
    Signup, Login, Notes, StudyPlan, QuizRequest,
    AssessmentRequest, ChatRequest, NoteCreate
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create database tables automatically
Base.metadata.create_all(bind=engine)

def seed_initial_data():
    """Initializes demo seed data in the database for instant testing and onboarding."""
    from models import User, Note, StudyPlan as StudyPlanModel, Quiz as QuizModel, History
    from authen import hashPassword
    db = SessionLocal()
    try:
        demo_user = db.query(User).filter(User.email == "student@nexora.ai").first()
        if not demo_user:
            demo_user = User(
                name="Nexora Student",
                email="student@nexora.ai",
                password=hashPassword("nexoraPassword123"),
                role="student"
            )
            db.add(demo_user)
            db.commit()
            db.refresh(demo_user)

        # Seed sample notes if empty
        user_notes = db.query(Note).filter((Note.user_email == "student@nexora.ai") | (Note.user_email == "guest@nexora.ai")).count()
        if user_notes == 0:
            sample_notes = [
                Note(
                    user_id=demo_user.id,
                    title="Cell Biology: Photosynthesis & Light Reactions",
                    content="Photosynthesis converts solar light energy into chemical energy stored in glucose. Light-dependent reactions generate ATP and NADPH in the thylakoid membranes, while the Calvin Cycle fixes CO2 into glyceraldehyde 3-phosphate.",
                    summary="Light reactions produce ATP & NADPH; the Calvin cycle uses them to synthesize glucose from CO2.",
                    tags="Biology",
                    source="manual",
                    user_email="student@nexora.ai"
                ),
                Note(
                    user_id=demo_user.id,
                    title="Physics: Newton's Laws & Dynamics",
                    content="First Law: Inertia. Second Law: F = ma. Third Law: For every action, there is an equal and opposite reaction. Momentum is conserved in isolated systems.",
                    summary="Newton's laws describe the relationship between an object's motion and the net forces acting upon it.",
                    tags="Physics",
                    source="manual",
                    user_email="student@nexora.ai"
                ),
                Note(
                    user_id=demo_user.id,
                    title="Computer Science: Asymptotic Analysis & Big-O",
                    content="Big-O notation describes the upper bound of an algorithm's runtime or space requirements as input size n grows to infinity. Key classes: O(1), O(log n), O(n), O(n log n), O(n^2).",
                    summary="Big-O classifies algorithm scalability and performance worst-case guarantees.",
                    tags="Computer Science",
                    source="manual",
                    user_email="student@nexora.ai"
                )
            ]
            db.add_all(sample_notes)

        # Seed sample study plan if empty
        plans_count = db.query(StudyPlanModel).filter(StudyPlanModel.user_email == "student@nexora.ai").count()
        if plans_count == 0:
            sample_plan = StudyPlanModel(
                user_id=demo_user.id,
                user_email="student@nexora.ai",
                topic="Quantum Mechanics Fundamentals",
                days=5,
                level="Intermediate",
                plan_text=(
                    "# 5-Day Quantum Mechanics Study Roadmap\n\n"
                    "## Day 1: Wave-Particle Duality & Planck Hypothesis\n"
                    "- Understand blackbody radiation and the photoelectric effect.\n"
                    "- Work through de Broglie wavelength calculations.\n\n"
                    "## Day 2: The Schrödinger Equation\n"
                    "- Time-independent vs. time-dependent formulation.\n"
                    "- Wavefunctions and probability densities.\n\n"
                    "## Day 3: Particle in a 1D Box\n"
                    "- Boundary conditions and quantization of energy levels.\n\n"
                    "## Day 4: Quantum Harmonic Oscillator\n"
                    "- Potential energy wells and zero-point energy.\n\n"
                    "## Day 5: Superposition & Measurement\n"
                    "- Quantum state collapse, Copenhagen interpretation, and practice exam."
                ),
                status="active"
            )
            db.add(sample_plan)

        # Seed sample history activity
        hist_count = db.query(History).filter(History.user_email == "student@nexora.ai").count()
        if hist_count == 0:
            db.add(History(
                user_id=demo_user.id,
                user_email="student@nexora.ai",
                item_type="study_plan",
                title="Study Plan: Quantum Mechanics Fundamentals",
                org_text="Topic: Quantum Mechanics Fundamentals, Days: 5",
                summary="5-Day Quantum Mechanics Study Roadmap created."
            ))

        db.commit()
    except Exception as e:
        logger.warning(f"Seed initial data note: {e}")
        db.rollback()
    finally:
        db.close()

# Execute initial seeding
seed_initial_data()

app = FastAPI(
    title="Nexora AI Study Platform API",
    description="Unified API Engine with full SQLAlchemy ORM & Alembic database integration",
    version="2.6.0"
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
        "version": "2.6.0",
        "database": "SQLAlchemy ORM + Alembic Migrations",
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
        "orm": "SQLAlchemy 2.x",
        "migrations": "Alembic",
        "service": "nexora-backend",
        "version": "2.6.0"
    }

# ----------------- Backward Compatibility Top-Level Routes -----------------
# Ensures frontend calls matching root paths work interchangeably

@app.post("/signup")
def root_signup(data: Signup, db: Session = Depends(get_db)):
    return auth_signup(data, db)

@app.post("/login")
def root_login(data: Login, db: Session = Depends(get_db)):
    return auth_login(data, db)

@app.get("/me")
def root_me(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security), db: Session = Depends(get_db)):
    return auth_me(credentials, db)

@app.post("/summarize")
def root_summarize(data: Notes, credentials: Optional[HTTPAuthorizationCredentials] = Depends(security), db: Session = Depends(get_db)):
    user_email = get_current_user_email(credentials)
    return notes_summarize(data, user_email, db)

@app.post("/quiz")
def root_quiz(data: QuizRequest, credentials: Optional[HTTPAuthorizationCredentials] = Depends(security), db: Session = Depends(get_db)):
    return assess_quiz(data, credentials, db)

@app.post("/study-plan")
def root_study_plan(data: StudyPlan, credentials: Optional[HTTPAuthorizationCredentials] = Depends(security), db: Session = Depends(get_db)):
    return study_gen(data, credentials, db)

@app.post("/assessment")
def root_assessment(data: AssessmentRequest, credentials: Optional[HTTPAuthorizationCredentials] = Depends(security), db: Session = Depends(get_db)):
    return assess_gen(data, credentials, db)

@app.post("/chat")
def root_chat(data: ChatRequest, credentials: Optional[HTTPAuthorizationCredentials] = Depends(security), db: Session = Depends(get_db)):
    return chat_gen(data, credentials, db)

@app.get("/stats")
def root_stats(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security), db: Session = Depends(get_db)):
    user_email = get_current_user_email(credentials)
    return stats_gen(user_email, db)

@app.get("/history")
def root_history(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security), db: Session = Depends(get_db)):
    user_email = get_current_user_email(credentials)
    return hist_gen(user_email, db)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
