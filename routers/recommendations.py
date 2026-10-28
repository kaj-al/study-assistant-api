from fastapi import APIRouter, Query, HTTPException
from schemas import RecommendationsRequest, RecommendationsResponse
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
