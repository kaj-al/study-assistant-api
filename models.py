from sqlalchemy import Column, Integer, String, Text, DateTime
from database import Base
import datetime

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Note(Base):
    __tablename__ = "notes"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, default="Untitled Note")
    content = Column(Text)
    summary = Column(Text, nullable=True)
    tags = Column(String, default="")
    user_email = Column(String, index=True, default="guest")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class History(Base):
    __tablename__ = "History"
    id = Column(Integer, primary_key=True, index=True)
    item_type = Column(String, default="general")
    org_text = Column(Text)
    summary = Column(Text)
    user_email = Column(String, index=True, default="guest")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)