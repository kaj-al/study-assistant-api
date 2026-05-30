from sqlalchemy import Column,Integer,String,Text
from database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True)
    password = Column(String)

class Note(Base):
    __tablename__ = "notes"
    id = Column(Integer, primary_key=True)
    content = Column(Text)
    summary = Column(Text)

# summary
class Summary(Base):
    __tablename__ = "History"
    id = Column(Integer,primary_key=True)
    org_text =Column(Text)
    summary = Column(Text)