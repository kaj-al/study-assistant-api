from pydantic import BaseModel
from typing import Optional, List, Any

class TextIn(BaseModel):
    text: str

class Notes(BaseModel):
    text: str

class SummaryResponse(BaseModel):
    summary: str
    key_points: Optional[List[str]] = []

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
