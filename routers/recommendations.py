import json
from fastapi import APIRouter, Query, HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional, List

from database import get_db
from models import SavedRecommendation as SavedRecModel, User, History
from schemas import (
    RecommendationsRequest,
    RecommendationsResponse,
    SavedRecommendationCreate,
    SavedRecommendationOut
)
from authen import security, get_current_user_email
from services import recommendation_service

router = APIRouter(prefix="/recommendations", tags=["Smart Recommendations"])

@router.get("", response_model=RecommendationsResponse)
def get_recommendations_query(
    topic: str = Query(..., min_length=1, description="Subject or weak topic to find resources for"),
    level: str = Query("College", description="Target academic level")
):
    """
    Core Recommendation Hub (reflecting tab4.py):
    Fetches real YouTube video courses, academic arXiv research papers, and curated documentation.
    """
    if not topic.strip():
        raise HTTPException(status_code=400, detail="Topic cannot be empty")
    return recommendation_service.get_all_recommendations(topic.strip(), level=level)

@router.post("", response_model=RecommendationsResponse)
def get_recommendations_post(data: RecommendationsRequest):
    """POST endpoint alternative for fetching smart learning resources."""
    if not data.topic or not data.topic.strip():
        raise HTTPException(status_code=400, detail="Topic cannot be empty")
    return recommendation_service.get_all_recommendations(data.topic.strip(), level=data.level or "College")

@router.post("/save", response_model=SavedRecommendationOut)
def save_recommendation(
    data: SavedRecommendationCreate,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Bookmarks a recommended video, paper, or document into user library."""
    user_email = get_current_user_email(credentials) or "guest@nexora.ai"
    user = db.query(User).filter(User.email == user_email).first()
    user_id = user.id if user else None

    meta_str = json.dumps(data.metadata) if data.metadata else "{}"

    new_rec = SavedRecModel(
        user_id=user_id,
        user_email=user_email,
        topic=data.topic,
        item_type=data.item_type,
        title=data.title,
        url=data.url,
        metadata_json=meta_str
    )
    db.add(new_rec)
    db.commit()
    db.refresh(new_rec)

    return {
        "id": new_rec.id,
        "topic": new_rec.topic,
        "item_type": new_rec.item_type,
        "title": new_rec.title,
        "url": new_rec.url,
        "metadata": data.metadata,
        "created_at": new_rec.created_at
    }

@router.get("/saved", response_model=List[SavedRecommendationOut])
def get_saved_recommendations(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Retrieves all bookmarked learning materials for the user."""
    user_email = get_current_user_email(credentials) or "guest@nexora.ai"
    items = db.query(SavedRecModel).filter(
        (SavedRecModel.user_email == user_email) | (SavedRecModel.user_email == "guest@nexora.ai")
    ).order_by(SavedRecModel.created_at.desc()).all()

    results = []
    for item in items:
        try:
            meta = json.loads(item.metadata_json) if item.metadata_json else {}
        except Exception:
            meta = {}
        results.append({
            "id": item.id,
            "topic": item.topic,
            "item_type": item.item_type,
            "title": item.title,
            "url": item.url,
            "metadata": meta,
            "created_at": item.created_at
        })
    return results

@router.delete("/saved/{rec_id}")
def delete_saved_recommendation(
    rec_id: int,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Removes a saved learning resource bookmark."""
    rec = db.query(SavedRecModel).filter(SavedRecModel.id == rec_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Saved recommendation not found")

    db.delete(rec)
    db.commit()
    return {"message": "Resource removed from saved bookmarks", "id": rec_id}
