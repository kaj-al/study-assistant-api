from pydantic import BaseModel
from typing import Optional, List, Dict, Any

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

class QuizOut(BaseModel):
    id: int
    topic: str
    difficulty: str
    num_questions: int
    paper: Optional[str] = None
    questions: Optional[List[Any]] = []
    created_at: Optional[Any] = None

class QuizAttemptOut(BaseModel):
    id: int
    quiz_id: Optional[int] = None
    topic: str
    total_questions: int
    correct_count: int
    score_percentage: float
    feedback: Optional[str] = ""
    created_at: Optional[Any] = None
    details: Optional[List[Dict[str, Any]]] = []
