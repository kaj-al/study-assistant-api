import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class SavedRecommendation(Base):
    __tablename__ = "saved_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    user_email = Column(String, index=True, default="guest")
    topic = Column(String, nullable=False)
    item_type = Column(String, nullable=False)  # "video", "paper", "doc"
    title = Column(String, nullable=False)
    url = Column(String, nullable=False)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="saved_recommendations")
