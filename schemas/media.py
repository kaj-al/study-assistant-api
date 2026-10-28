from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class YouTubeIn(BaseModel):
    url: str

class YouTubeNotesResponse(BaseModel):
    title: str
    duration: Optional[int] = None
    transcript: str
    summary: str
    notes: str
    quiz: Optional[List[Dict[str, Any]]] = []

class MediaTranscriptOut(BaseModel):
    id: int
    title: str
    source_type: str
    source_url_or_filename: Optional[str] = ""
    duration: Optional[int] = None
    transcript: str
    summary: Optional[str] = ""
    notes: Optional[str] = ""
    created_at: Optional[Any] = None
