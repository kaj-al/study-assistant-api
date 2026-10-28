from .auth import Signup, Login, TokenResponse, AuthVerifyResponse
from .note import TextIn, Notes, SummaryResponse, NoteCreate, NoteOut
from .study import StudyPlan, StudyPlanResponse, StudyPlanOut, StudyPlanUpdate
from .assessment import (
    QuizQuestion,
    QuizRequest,
    QuizResponse,
    AssessmentRequest,
    AssessmentResponse,
    QuizSubmitRequest,
    QuizSubmitResponse,
    QuizOut,
    QuizAttemptOut
)
from .chat import ChatMessage, ChatRequest, ChatResponse, ChatSessionOut, ChatMessageOut
from .media import YouTubeIn, YouTubeNotesResponse, MediaTranscriptOut
from .recommendation import (
    VideoItem,
    PaperItem,
    DocItem,
    RecommendationsRequest,
    RecommendationsResponse,
    SavedRecommendationCreate,
    SavedRecommendationOut
)
from .analytics import DashboardStats

__all__ = [
    "Signup",
    "Login",
    "TokenResponse",
    "AuthVerifyResponse",
    "TextIn",
    "Notes",
    "SummaryResponse",
    "NoteCreate",
    "NoteOut",
    "StudyPlan",
    "StudyPlanResponse",
    "StudyPlanOut",
    "StudyPlanUpdate",
    "QuizQuestion",
    "QuizRequest",
    "QuizResponse",
    "AssessmentRequest",
    "AssessmentResponse",
    "QuizSubmitRequest",
    "QuizSubmitResponse",
    "QuizOut",
    "QuizAttemptOut",
    "ChatMessage",
    "ChatRequest",
    "ChatResponse",
    "ChatSessionOut",
    "ChatMessageOut",
    "YouTubeIn",
    "YouTubeNotesResponse",
    "MediaTranscriptOut",
    "VideoItem",
    "PaperItem",
    "DocItem",
    "RecommendationsRequest",
    "RecommendationsResponse",
    "SavedRecommendationCreate",
    "SavedRecommendationOut",
    "DashboardStats"
]
