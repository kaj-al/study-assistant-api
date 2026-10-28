import json
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from database import get_db
from models import Quiz as QuizModel, QuizAttempt as QuizAttemptModel, User, History
from schemas import (
    QuizRequest,
    QuizResponse,
    QuizQuestion,
    AssessmentRequest,
    AssessmentResponse,
    QuizSubmitRequest,
    QuizSubmitResponse,
    QuizOut,
    QuizAttemptOut
)
from authen import security, get_current_user_email
from services import llm_service

router = APIRouter(prefix="/assessment", tags=["Assessment & Quiz"])

def format_quiz_questions(raw_questions: List[Dict[str, Any]]) -> List[QuizQuestion]:
    questions = []
    for idx, q in enumerate(raw_questions):
        raw_options = q.get("options", ["Option A", "Option B", "Option C", "Option D"])
        raw_correct = str(q.get("correct_answer", "")).strip()

        # Find option letter A, B, C, or D
        opt_letter = "A"
        if raw_correct.upper() in ["A", "B", "C", "D"]:
            opt_letter = raw_correct.upper()
        elif len(raw_correct) >= 2 and raw_correct[0].upper() in ["A", "B", "C", "D"] and raw_correct[1] in [")", ".", ":", " "]:
            opt_letter = raw_correct[0].upper()
        else:
            for i, opt in enumerate(raw_options):
                clean_opt = str(opt).strip()
                if raw_correct.lower() in clean_opt.lower() or clean_opt.lower() in raw_correct.lower():
                    opt_letter = chr(65 + i)
                    break

        clean_options = []
        for i, opt in enumerate(raw_options):
            letter = chr(65 + i)
            text = str(opt).strip()
            if len(text) >= 2 and text[0].upper() == letter and text[1] in [")", ".", ":", " "]:
                text = text[2:].strip()
            clean_options.append(f"{letter}) {text}")

        idx_in_opt = ord(opt_letter) - 65
        correct_full = clean_options[idx_in_opt] if 0 <= idx_in_opt < len(clean_options) else clean_options[0]

        questions.append(QuizQuestion(
            id=q.get("id", idx + 1),
            question=q.get("question", "Question"),
            options=clean_options,
            correct_answer=correct_full,
            answer=opt_letter,
            explanation=q.get("explanation", "Correct based on theoretical guidelines.")
        ))
    return questions

@router.post("/quiz", response_model=QuizResponse)
def generate_quiz(
    data: QuizRequest,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Generates structured interactive multiple choice questions and saves them to the database."""
    content = data.text or data.topic
    if not content or not content.strip():
        raise HTTPException(status_code=400, detail="Topic or text is required")

    num_q = max(1, min(data.num_questions or 3, 10))
    raw_questions = llm_service.generate_quiz_json(content, num_questions=num_q)
    questions = format_quiz_questions(raw_questions)
    topic_str = data.topic or "Selected Study Material"

    user_email = get_current_user_email(credentials) or "guest@nexora.ai"
    user = db.query(User).filter(User.email == user_email).first()
    user_id = user.id if user else None

    # Persist generated quiz
    try:
        q_dict_list = [q.dict() for q in questions]
        new_quiz = QuizModel(
            user_id=user_id,
            user_email=user_email,
            topic=topic_str,
            difficulty=data.difficulty or "Medium",
            num_questions=len(questions),
            questions_data=json.dumps(q_dict_list)
        )
        db.add(new_quiz)

        hist = History(
            user_id=user_id,
            user_email=user_email,
            item_type="quiz",
            title=f"Quiz: {topic_str}",
            org_text=f"Questions: {len(questions)}",
            summary=f"Generated {len(questions)} quiz questions for {topic_str}"
        )
        db.add(hist)
        db.commit()
    except Exception:
        db.rollback()

    return {
        "topic": topic_str,
        "questions": questions
    }

@router.post("", response_model=AssessmentResponse)
@router.post("/generate", response_model=AssessmentResponse)
def generate_assessment_paper(
    data: AssessmentRequest,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Generates a complete formal examination paper and structured questions, storing it in the database."""
    if not data.topic or not data.topic.strip():
        raise HTTPException(status_code=400, detail="Topic is required")

    difficulty = data.difficulty or "Medium"
    num_q = max(3, min(data.num_questions or 5, 20))

    paper = llm_service.generate_assessment_paper(data.topic, difficulty=difficulty, num_questions=num_q)
    raw_questions = llm_service.generate_quiz_json(data.topic, num_questions=min(num_q, 5))
    questions = format_quiz_questions(raw_questions)

    user_email = get_current_user_email(credentials) or "guest@nexora.ai"
    user = db.query(User).filter(User.email == user_email).first()
    user_id = user.id if user else None

    try:
        q_dict_list = [q.dict() for q in questions]
        new_quiz = QuizModel(
            user_id=user_id,
            user_email=user_email,
            topic=data.topic.strip(),
            difficulty=difficulty,
            num_questions=num_q,
            paper_text=paper,
            questions_data=json.dumps(q_dict_list)
        )
        db.add(new_quiz)

        hist = History(
            user_id=user_id,
            user_email=user_email,
            item_type="assessment",
            title=f"Exam Paper: {data.topic.strip()}",
            org_text=f"Difficulty: {difficulty}, Questions: {num_q}",
            summary=paper[:400]
        )
        db.add(hist)
        db.commit()
    except Exception:
        db.rollback()

    return {
        "topic": data.topic,
        "difficulty": difficulty,
        "num_questions": num_q,
        "paper": paper,
        "questions": questions
    }

@router.post("/submit", response_model=QuizSubmitResponse)
def submit_quiz(
    data: QuizSubmitRequest,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Scores user quiz answers, provides instant feedback, and records attempt metrics in the database."""
    user_answers = data.answers or {}
    questions = data.questions or []

    correct_count = 0
    total = len(questions) if questions else len(user_answers)
    details = []

    import re
    for q in questions:
        q_id = str(q.id)
        chosen = user_answers.get(q_id, "").strip()

        # Letter extraction: e.g. "A" from "A", "A)", "A) Option text"
        chosen_clean = chosen.upper().strip()
        chosen_letter = chosen_clean[0] if (chosen_clean and chosen_clean[0] in "ABCD") else ""

        target_letter = (q.answer or "").upper().strip()
        if not target_letter and q.correct_answer:
            target_clean = q.correct_answer.upper().strip()
            target_letter = target_clean[0] if (target_clean and target_clean[0] in "ABCD") else ""

        clean_chosen_text = re.sub(r'^[A-D][\)\.\:\s]+', '', chosen, flags=re.IGNORECASE).strip().lower()
        clean_correct_text = re.sub(r'^[A-D][\)\.\:\s]+', '', q.correct_answer, flags=re.IGNORECASE).strip().lower()

        is_correct = False
        if chosen_letter and target_letter and chosen_letter == target_letter:
            is_correct = True
        elif clean_chosen_text and clean_correct_text and (clean_chosen_text == clean_correct_text or clean_chosen_text in clean_correct_text or clean_correct_text in clean_chosen_text):
            is_correct = True
        elif chosen.strip().lower() == q.correct_answer.strip().lower():
            is_correct = True

        if is_correct:
            correct_count += 1
        details.append({
            "question_id": q.id,
            "question": q.question,
            "chosen_answer": chosen,
            "correct_answer": q.correct_answer,
            "is_correct": is_correct,
            "explanation": q.explanation
        })

    score_pct = round((correct_count / max(total, 1)) * 100, 1)

    if score_pct >= 80:
        feedback = "Outstanding performance! You have demonstrated strong mastery over these core concepts."
    elif score_pct >= 50:
        feedback = "Good foundation! Review the questions you missed to reinforce your understanding."
    else:
        feedback = "Keep practicing! We recommend reviewing the lecture notes and taking advantage of the AI Tutor Chat."

    user_email = get_current_user_email(credentials) or "guest@nexora.ai"
    user = db.query(User).filter(User.email == user_email).first()
    user_id = user.id if user else None

    # Save QuizAttempt to database
    try:
        attempt = QuizAttemptModel(
            user_id=user_id,
            user_email=user_email,
            topic=questions[0].question[:50] if questions else "General Quiz",
            total_questions=total,
            correct_count=correct_count,
            score_percentage=score_pct,
            feedback=feedback,
            answers_data=json.dumps(details)
        )
        db.add(attempt)

        hist = History(
            user_id=user_id,
            user_email=user_email,
            item_type="quiz_attempt",
            title=f"Quiz Result: {score_pct}% ({correct_count}/{total})",
            org_text=f"Total: {total}, Correct: {correct_count}",
            summary=feedback
        )
        db.add(hist)
        db.commit()
    except Exception:
        db.rollback()

    return {
        "total_questions": total,
        "correct_count": correct_count,
        "score_percentage": score_pct,
        "feedback": feedback,
        "details": details
    }

@router.get("/quizzes", response_model=List[QuizOut])
def get_user_quizzes(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Retrieves all quizzes created for the user."""
    user_email = get_current_user_email(credentials) or "guest@nexora.ai"
    quizzes = db.query(QuizModel).filter(
        (QuizModel.user_email == user_email) | (QuizModel.user_email == "guest@nexora.ai")
    ).order_by(QuizModel.created_at.desc()).all()

    results = []
    for q in quizzes:
        try:
            questions_list = json.loads(q.questions_data) if q.questions_data else []
        except Exception:
            questions_list = []
        results.append({
            "id": q.id,
            "topic": q.topic,
            "difficulty": q.difficulty,
            "num_questions": q.num_questions,
            "paper": q.paper_text,
            "questions": questions_list,
            "created_at": q.created_at
        })
    return results

@router.get("/attempts", response_model=List[QuizAttemptOut])
def get_user_quiz_attempts(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """Retrieves past quiz attempts with scores and feedback."""
    user_email = get_current_user_email(credentials) or "guest@nexora.ai"
    attempts = db.query(QuizAttemptModel).filter(
        (QuizAttemptModel.user_email == user_email) | (QuizAttemptModel.user_email == "guest@nexora.ai")
    ).order_by(QuizAttemptModel.created_at.desc()).all()

    results = []
    for a in attempts:
        try:
            details_list = json.loads(a.answers_data) if a.answers_data else []
        except Exception:
            details_list = []
        results.append({
            "id": a.id,
            "quiz_id": a.quiz_id,
            "topic": a.topic,
            "total_questions": a.total_questions,
            "correct_count": a.correct_count,
            "score_percentage": a.score_percentage,
            "feedback": a.feedback,
            "details": details_list,
            "created_at": a.created_at
        })
    return results
