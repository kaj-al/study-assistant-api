from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from database import SessionLocal
from models import Note, History
from schemas import Notes, SummaryResponse, NoteCreate, NoteOut, TextIn
from authen import get_current_user_email
from services import llm_service

router = APIRouter(prefix="/notes", tags=["Notes & Summaries"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/summarize", response_model=SummaryResponse)
def summarize(data: Notes, user_email: Optional[str] = Depends(get_current_user_email), db: Session = Depends(get_db)):
    """Quick high-yield AI summary with key takeaways."""
    if not data.text or not data.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    res = llm_service.generate_summary(data.text)
    
    # Save to history
    try:
        hist = History(item_type="summary", org_text=data.text[:1000], summary=res.get("summary", ""), user_email=user_email or "guest")
        db.add(hist)
        db.commit()
    except Exception:
        db.rollback()

    return res

@router.post("/generate")
def generate_notes(data: TextIn, user_email: Optional[str] = Depends(get_current_user_email), db: Session = Depends(get_db)):
    """Generate structured markdown lecture notes with subtopics, definitions, and flashpoints."""
    if not data.text or not data.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    notes_content = llm_service.generate_structured_notes(data.text)
    return {"notes": notes_content}

@router.get("", response_model=List[NoteOut])
def get_user_notes(user_email: Optional[str] = Depends(get_current_user_email), db: Session = Depends(get_db)):
    """Retrieves all notes saved by the user."""
    notes = db.query(Note).filter((Note.user_email == user_email) | (Note.user_email == "guest")).order_by(Note.created_at.desc()).all()
    return notes

@router.post("", status_code=status.HTTP_201_CREATED)
@router.post("/save")
def save_note(note_data: NoteCreate, user_email: Optional[str] = Depends(get_current_user_email), db: Session = Depends(get_db)):
    """Saves a new note to user notebook database."""
    new_note = Note(
        title=note_data.title or "Untitled Note",
        content=note_data.content,
        summary=note_data.summary or "",
        tags=note_data.tags or "General",
        user_email=user_email or "guest"
    )
    db.add(new_note)
    db.commit()
    db.refresh(new_note)
    return {"message": "Note saved successfully", "note": new_note}

@router.delete("/{note_id}")
def delete_note(note_id: int, user_email: Optional[str] = Depends(get_current_user_email), db: Session = Depends(get_db)):
    """Deletes a note by ID."""
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    db.delete(note)
    db.commit()
    return {"message": "Note deleted successfully", "id": note_id}
