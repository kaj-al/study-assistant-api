# Nexora - Backend API (`APIDoc`)

High-performance AI API built with **FastAPI**, **SQLAlchemy ORM**, **Alembic**, and **Groq Cloud LLMs**.

---

## 📁 Clean Directory Structure

```text
APIDoc/
├── alembic/                    # Database schema migration scripts & versions
├── models/                     # SQLAlchemy ORM Database Models
│   ├── assessment.py           # Quiz & exam attempt models
│   ├── chat.py                 # Persistent tutor chat sessions & messages
│   ├── history.py              # Activity audit log & history trail
│   ├── media.py                # YouTube & lecture video transcripts
│   ├── note.py                 # User notes, markdown summaries & tags
│   ├── recommendation.py       # Saved papers, articles & videos
│   ├── study.py                # Multi-day study roadmap planner
│   └── user.py                 # User authentication & profile records
│
├── routers/                    # FastAPI APIRouter endpoints
│   ├── analytics.py            # Aggregate learning stats & hours
│   ├── assessment.py           # AI quiz generator & grading
│   ├── auth.py                 # Signup, login, JWT & profile
│   ├── chat.py                 # Multi-turn conversational AI tutor
│   ├── media.py                # Video transcription & processing
│   ├── notes.py                # Structured notes & summarization
│   ├── recommendations.py      # Curated resource discovery
│   └── study.py                # Structured study roadmaps
│
├── schemas/                    # Pydantic request & response validation
│   ├── analytics.py
│   ├── assessment.py
│   ├── auth.py
│   ├── chat.py
│   ├── media.py
│   ├── note.py
│   ├── recommendation.py
│   └── study.py
│
├── services/                   # Core business logic & AI orchestration
│   ├── llm_service.py          # Groq LLM prompts & structured responses
│   ├── recommendation_service.py # Smart study recommendations engine
│   └── transcription_service.py  # Audio/video transcription engine
│
├── authen.py                   # JWT generation, validation & password hashing
├── config.py                   # Environment variables & runtime settings
├── database.py                 # SQLAlchemy engine, SessionLocal & get_db
├── main.py                     # FastAPI application setup, CORS & router registration
├── requirements.txt            # Python dependencies
└── alembic.ini                 # Alembic configuration
```

---

## 🚀 Running the Backend

```bash
# From workspace root:
python run_backend.py

# Or from inside APIDoc directory:
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

- **Base URL**: `http://127.0.0.1:8000`
- **Interactive Swagger Docs**: `http://127.0.0.1:8000/docs`
- **ReDoc**: `http://127.0.0.1:8000/redoc`
