import os
import tempfile
import logging
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials
from starlette.background import BackgroundTask
from sqlalchemy.orm import Session

from database import get_db
from models import MediaTranscript as MediaTranscriptModel, User, History
from schemas import YouTubeIn, YouTubeNotesResponse, TextIn, MediaTranscriptOut
from authen import security, get_current_user_email
from services import transcription_service, llm_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/media", tags=["Media & Audio Notes"])

def remove_file(path: str):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass

@router.post("/youtube-notes", response_model=YouTubeNotesResponse)
def youtube_notes(
    data: YouTubeIn,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Core Nexora Feature: Extracts audio/transcript from YouTube URL,
    transcribes it, produces structured lecture notes, and saves to database.
    """
    if not data.url or not data.url.strip():
        raise HTTPException(status_code=400, detail="YouTube URL is required")

    user_email = get_current_user_email(credentials) or "guest@nexora.ai"
    user = db.query(User).filter(User.email == user_email).first()
    user_id = user.id if user else None

    try:
        result = transcription_service.process_youtube_notes(data.url.strip())
    except Exception as e:
        logger.exception(f"Error processing YouTube notes: {e}")
        raise HTTPException(status_code=422, detail=f"YouTube transcription failed: {str(e)}")

    # Persist transcript in database
    try:
        media_rec = MediaTranscriptModel(
            user_id=user_id,
            user_email=user_email,
            title=result.get("title", "YouTube Lecture"),
            source_type="youtube",
            source_url_or_filename=data.url.strip(),
            duration=result.get("duration"),
            transcript=result.get("transcript", ""),
            summary=result.get("summary", ""),
            notes=result.get("notes", "")
        )
        db.add(media_rec)

        hist = History(
            user_id=user_id,
            user_email=user_email,
            item_type="youtube_notes",
            title=result.get("title", "YouTube Lecture"),
            org_text=data.url.strip(),
            summary=result.get("summary", "")[:400]
        )
        db.add(hist)
        db.commit()
    except Exception:
        db.rollback()

    return result

ALLOWED_MEDIA_EXTENSIONS = {
    ".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac",
    ".mp4", ".mov", ".mkv", ".avi", ".webm", ".flv", ".wmv"
}

@router.post("/upload-notes")
async def upload_notes(
    file: UploadFile = File(...),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Upload an audio or video lecture file.
    Transcribes speech and produces structured notes, persisting to database.
    """
    suffix = Path(file.filename or "media.wav").suffix.lower()
    if suffix not in ALLOWED_MEDIA_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format {suffix}. Allowed: {', '.join(sorted(ALLOWED_MEDIA_EXTENSIONS))}"
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp_path = tmp.name
        content = await file.read()
        tmp.write(content)

    user_email = get_current_user_email(credentials) or "guest@nexora.ai"
    user = db.query(User).filter(User.email == user_email).first()
    user_id = user.id if user else None

    try:
        result = transcription_service.process_media_file_notes(tmp_path, file.filename or "Lecture")
        
        # Persist in database
        try:
            media_rec = MediaTranscriptModel(
                user_id=user_id,
                user_email=user_email,
                title=file.filename or "Audio/Video Lecture",
                source_type="upload",
                source_url_or_filename=file.filename or "uploaded_media",
                duration=result.get("duration"),
                transcript=result.get("transcript", ""),
                summary=result.get("summary", ""),
                notes=result.get("notes", "")
            )
            db.add(media_rec)

            hist = History(
                user_id=user_id,
                user_email=user_email,
                item_type="audio_notes",
                title=file.filename or "Audio/Video Lecture",
                org_text=f"Uploaded file: {file.filename}",
                summary=result.get("summary", "")[:400]
            )
            db.add(hist)
            db.commit()
        except Exception:
            db.rollback()

        return result
    except Exception as e:
        logger.exception(f"Error processing media upload: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription processing error: {str(e)}")
    finally:
        remove_file(tmp_path)

@router.post("/transcribe")
async def transcribe_only(file: UploadFile = File(...)):
    """Uploads audio or video file and returns verbatim transcript text."""
    suffix = Path(file.filename or "media.wav").suffix.lower()
    if suffix not in ALLOWED_MEDIA_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format {suffix}. Allowed: {', '.join(sorted(ALLOWED_MEDIA_EXTENSIONS))}"
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp_path = tmp.name
        content = await file.read()
        tmp.write(content)

    target_audio = tmp_path
    cleanup_audio = False
    if suffix in {".mp4", ".mov", ".mkv", ".avi", ".webm", ".flv", ".wmv"}:
        target_audio = transcription_service.extract_audio_from_video(tmp_path)
        cleanup_audio = True

    try:
        transcript = transcription_service.transcribe_audio_file(target_audio)
        return {"filename": file.filename, "transcript": transcript}
    except Exception as e:
        logger.exception(f"Error transcribing media: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription error: {str(e)}")
    finally:
        if cleanup_audio and target_audio and os.path.exists(target_audio):
            remove_file(target_audio)
        remove_file(tmp_path)

@router.post("/youtube-audio")
def youtube_audio(data: YouTubeIn):
    """Downloads YouTube audio and streams back as attachment."""
    try:
        audio_path, title, duration = transcription_service.download_youtube_audio_fallback(data.url)
        return FileResponse(
            audio_path,
            media_type="audio/mpeg",
            filename=f"{Path(audio_path).name}",
            background=BackgroundTask(remove_file, audio_path)
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to fetch YouTube audio: {str(e)}")

@router.get("/transcripts", response_model=List[MediaTranscriptOut])
def get_user_media_transcripts(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Retrieves all media transcripts and lecture notes saved by the user."""
    user_email = get_current_user_email(credentials) or "guest@nexora.ai"
    items = db.query(MediaTranscriptModel).filter(
        (MediaTranscriptModel.user_email == user_email) | (MediaTranscriptModel.user_email == "guest@nexora.ai")
    ).order_by(MediaTranscriptModel.created_at.desc()).all()

    return [
        {
            "id": item.id,
            "title": item.title,
            "source_type": item.source_type,
            "source_url_or_filename": item.source_url_or_filename or "",
            "duration": item.duration,
            "transcript": item.transcript,
            "summary": item.summary,
            "notes": item.notes,
            "created_at": item.created_at
        }
        for item in items
    ]

@router.get("/transcripts/{transcript_id}", response_model=MediaTranscriptOut)
def get_media_transcript_by_id(
    transcript_id: int,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Retrieves a single transcript by ID."""
    item = db.query(MediaTranscriptModel).filter(MediaTranscriptModel.id == transcript_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Media transcript not found")
    return {
        "id": item.id,
        "title": item.title,
        "source_type": item.source_type,
        "source_url_or_filename": item.source_url_or_filename or "",
        "duration": item.duration,
        "transcript": item.transcript,
        "summary": item.summary,
        "notes": item.notes,
        "created_at": item.created_at
    }

@router.delete("/transcripts/{transcript_id}")
def delete_media_transcript(
    transcript_id: int,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Deletes a media transcript from the database."""
    item = db.query(MediaTranscriptModel).filter(MediaTranscriptModel.id == transcript_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Media transcript not found")

    db.delete(item)
    db.commit()
    return {"message": "Media transcript deleted successfully", "id": transcript_id}
