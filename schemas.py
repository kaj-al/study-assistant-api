from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict

class Signup(BaseModel):
    name: str
    email: str
    password: str

class Login(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Optional[Dict[str, Any]] = None

class AuthVerifyResponse(BaseModel):
    verified: bool
    user: Optional[Dict[str, Any]] = None
    email: Optional[str] = None
    message: Optional[str] = "Authentication successful"

class TextIn(BaseModel):
    text: str

class Notes(BaseModel):
    text: str

class YouTubeIn(BaseModel):
    url: str

class YouTubeNotesResponse(BaseModel):
    title: str
    duration: Optional[int] = None
    transcript: str
    summary: str
    notes: str
    quiz: Optional[List[Dict[str, Any]]] = []

class SummaryResponse(BaseModel):
    summary: str
    key_points: Optional[List[str]] = []

class StudyPlan(BaseModel):
    topic: str
    days: int = 7
    level: Optional[str] = "Intermediate"

class StudyPlanResponse(BaseModel):
    topic: str
    days: int
    level: str
    plan: str

class QuizQuestion(BaseModel):
    id: int
    question: str
    options: List[str]
    correct_answer: str
    answer: Optional[str] = "A"
    explanation: Optional[str] = ""

class QuizRequest(BaseModel):
    text: Optional[str] = ""
    topic: Optional[str] = ""
    num_questions: Optional[int] = 3
    difficulty: Optional[str] = "Medium"

class QuizResponse(BaseModel):
    topic: Optional[str] = "General"
    questions: List[QuizQuestion]

class AssessmentRequest(BaseModel):
    topic: str
    difficulty: Optional[str] = "Medium"
    num_questions: Optional[int] = 5

class AssessmentResponse(BaseModel):
    topic: str
    difficulty: str
    num_questions: int
    paper: str
    questions: Optional[List[QuizQuestion]] = []

class QuizSubmitRequest(BaseModel):
    answers: Dict[str, str]  # question_id -> chosen option
    questions: Optional[List[QuizQuestion]] = []

class QuizSubmitResponse(BaseModel):
    total_questions: int
    correct_count: int
    score_percentage: float
    feedback: str
    details: List[Dict[str, Any]]

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = []
    language: Optional[str] = "English"

class ChatResponse(BaseModel):
    reply: str
    action_type: Optional[str] = "explanation"  # "explanation", "question", "feedback"

class RecommendationsRequest(BaseModel):
    topic: str
    level: Optional[str] = "College"

class VideoItem(BaseModel):
    title: str
    url: str
    duration: Optional[int] = None
    channel: Optional[str] = None
    thumbnail: Optional[str] = None

class PaperItem(BaseModel):
    title: str
    url: str
    summary: Optional[str] = ""
    pdf_url: Optional[str] = ""
    arxiv_id: Optional[str] = ""

class DocItem(BaseModel):
    title: str
    url: str
    snippet: Optional[str] = ""
    source: Optional[str] = "Official Documentation"

class RecommendationsResponse(BaseModel):
    topic: str
    videos: List[VideoItem]
    papers: List[PaperItem]
    docs: List[DocItem]

class NoteCreate(BaseModel):
    title: str
    content: str
    summary: Optional[str] = ""
    tags: Optional[str] = ""

class NoteOut(BaseModel):
    id: int
    title: str
    content: str
    summary: Optional[str] = ""
    tags: Optional[str] = ""
    created_at: Optional[Any] = None
    user_email: Optional[str] = ""

class DashboardStats(BaseModel):
    total_notes: int
    total_quizzes: int
    study_hours: float
    mastery_score: str