from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from models import Note, History, User
from schemas import Notes, SummaryResponse, NoteCreate, NoteOut, TextIn
from authen import get_current_user_email
from services import llm_service

router = APIRouter(prefix="/notes", tags=["Notes & Summaries"])

@router.post("/summarize", response_model=SummaryResponse)
def summarize(data: Notes, user_email: Optional[str] = Depends(get_current_user_email), db: Session = Depends(get_db)):
    """Quick high-yield AI summary with key takeaways."""
    if not data.text or not data.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    res = llm_service.generate_summary(data.text)
    user_email_str = user_email or "guest@nexora.ai"
    user = db.query(User).filter(User.email == user_email_str).first()
    user_id = user.id if user else None
    
    # Save to history
    try:
        hist = History(
            user_id=user_id,
            user_email=user_email_str,
            item_type="summary",
            title="Text Summary",
            org_text=data.text[:1000],
            summary=res.get("summary", "")
        )
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
    email_filter = user_email or "guest@nexora.ai"
    notes = db.query(Note).filter(
        (Note.user_email == email_filter) | (Note.user_email == "guest@nexora.ai") | (Note.user_email == "guest") | (Note.user_email == "student@nexora.ai")
    ).order_by(Note.created_at.desc()).all()
    return notes

@router.post("", status_code=status.HTTP_201_CREATED)
@router.post("/save")
def save_note(note_data: NoteCreate, user_email: Optional[str] = Depends(get_current_user_email), db: Session = Depends(get_db)):
    """Saves a new note to user notebook database."""
    email_str = user_email or "guest@nexora.ai"
    user = db.query(User).filter(User.email == email_str).first()
    user_id = user.id if user else None

    new_note = Note(
        user_id=user_id,
        user_email=email_str,
        title=note_data.title or "Untitled Note",
        content=note_data.content,
        summary=note_data.summary or "",
        tags=note_data.tags or "General",
        source="manual"
    )
    db.add(new_note)
    db.commit()
    db.refresh(new_note)
    return {"message": "Note saved successfully", "note": new_note}

@router.put("/{note_id}")
def update_note(note_id: int, note_data: NoteCreate, user_email: Optional[str] = Depends(get_current_user_email), db: Session = Depends(get_db)):
    """Updates an existing note."""
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    if note_data.title is not None:
        note.title = note_data.title
    if note_data.content is not None:
        note.content = note_data.content
    if note_data.summary is not None:
        note.summary = note_data.summary
    if note_data.tags is not None:
        note.tags = note_data.tags

    db.commit()
    db.refresh(note)
    return {"message": "Note updated successfully", "note": note}

@router.delete("/{note_id}")
def delete_note(note_id: int, user_email: Optional[str] = Depends(get_current_user_email), db: Session = Depends(get_db)):
    """Deletes a note by ID."""
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    db.delete(note)
    db.commit()
    return {"message": "Note deleted successfully", "id": note_id}
