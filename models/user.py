import datetime
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, default="student")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    notes = relationship("Note", back_populates="user", cascade="all, delete-orphan", foreign_keys="Note.user_id")
    study_plans = relationship("StudyPlan", back_populates="user", cascade="all, delete-orphan")
    quizzes = relationship("Quiz", back_populates="user", cascade="all, delete-orphan")
    quiz_attempts = relationship("QuizAttempt", back_populates="user", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
    media_transcripts = relationship("MediaTranscript", back_populates="user", cascade="all, delete-orphan")
    saved_recommendations = relationship("SavedRecommendation", back_populates="user", cascade="all, delete-orphan")
    history_items = relationship("History", back_populates="user", cascade="all, delete-orphan")
