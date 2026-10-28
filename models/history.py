import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class History(Base):
    __tablename__ = "History"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    user_email = Column(String, index=True, default="guest")
    item_type = Column(String, default="general")
    title = Column(String, default="")
    org_text = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    extra_data = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="history_items")
