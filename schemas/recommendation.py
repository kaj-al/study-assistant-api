from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class VideoItem(BaseModel):
    title: str
    url: str
    duration: Optional[int] = None
    channel: Optional[str] = None
    thumbnail: Optional[str] = None

class PaperItem(BaseModel):
    title: str
    url: str
    summary: Optional[str] = ""
    pdf_url: Optional[str] = ""
    arxiv_id: Optional[str] = ""

class DocItem(BaseModel):
    title: str
    url: str
    snippet: Optional[str] = ""
    source: Optional[str] = "Official Documentation"

class RecommendationsRequest(BaseModel):
    topic: str
    level: Optional[str] = "College"

class RecommendationsResponse(BaseModel):
    topic: str
    videos: List[VideoItem]
    papers: List[PaperItem]
    docs: List[DocItem]

class SavedRecommendationCreate(BaseModel):
    topic: str
    item_type: str  # video, paper, doc
    title: str
    url: str
    metadata: Optional[Dict[str, Any]] = None

class SavedRecommendationOut(BaseModel):
    id: int
    topic: str
    item_type: str
    title: str
    url: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[Any] = None
