# Nexora AI Study Platform - API Documentation

An AI-powered FastAPI backend powering the Nexora Web Application.

## Base URL
`http://127.0.0.1:8000`

## Interactive Documentation
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## Tech Stack
- **Framework**: FastAPI
- **Database**: SQLite with SQLAlchemy ORM
- **Authentication**: JWT (JSON Web Tokens) with Bcrypt password hashing
- **AI Engine**: Groq Cloud LLM (`openai/gpt-oss-120b`, `openai/gpt-oss-20b`, `qwen/qwen3.8-27b`)
- **CORS**: Configured for Next.js frontend (`*`)

---

## Key Endpoints

### 1. Health & Status
- `GET /` - Root health check & API status
- `GET /health` - Database & service status

### 2. Authentication
- `POST /signup` - Register a new student account
- `POST /login` - Log in and receive JWT `access_token`
- `GET /me` - Retrieve authenticated user profile (requires `Bearer` token)

### 3. AI Learning Tools
- `POST /summarize` - Summarize educational notes into overview + key bullet points
- `POST /quiz` - Generate multiple-choice quiz questions with answers and explanations
- `POST /study-plan` - Build structured day-by-day study roadmap for any topic and duration
- `POST /chat` - Interactive AI Tutor for answering study questions and doubt solving
- `POST /assessment` - Generate university/school level examination papers
- `POST /notes/generate` - Generate full structured study notes from raw material

### 4. Notes & Database Storage
- `POST /notes/save` - Save study note/summary to SQLite
- `GET /notes` - Retrieve saved notes
- `DELETE /notes/{id}` - Delete a saved note
- `GET /history` - Recent generation logs
- `GET /stats` - Study metrics (hours, quiz counts, notes count)

---

## Running the API
```bash
python run_backend.py
```
Or directly with Uvicorn:
```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```
