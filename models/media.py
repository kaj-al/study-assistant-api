import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class MediaTranscript(Base):
    __tablename__ = "media_transcripts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    user_email = Column(String, index=True, default="guest")
    title = Column(String, default="Media Lecture")
    source_type = Column(String, default="youtube")  # "youtube", "upload"
    source_url_or_filename = Column(String, nullable=True)
    duration = Column(Integer, nullable=True)
    transcript = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="media_transcripts")
