from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

from schemas import (
    QuizRequest,
    QuizResponse,
    QuizQuestion,
    AssessmentRequest,
    AssessmentResponse,
    QuizSubmitRequest,
    QuizSubmitResponse
)
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
def generate_quiz(data: QuizRequest):
    """Generates structured interactive multiple choice questions."""
    content = data.text or data.topic
    if not content or not content.strip():
        raise HTTPException(status_code=400, detail="Topic or text is required")

    num_q = max(1, min(data.num_questions or 3, 10))
    raw_questions = llm_service.generate_quiz_json(content, num_questions=num_q)
    questions = format_quiz_questions(raw_questions)

    return {
        "topic": data.topic or "Selected Study Material",
        "questions": questions
    }

@router.post("/generate", response_model=AssessmentResponse)
def generate_assessment_paper(data: AssessmentRequest):
    """Generates a complete formal examination / assessment paper."""
    if not data.topic or not data.topic.strip():
        raise HTTPException(status_code=400, detail="Topic is required")

    difficulty = data.difficulty or "Medium"
    num_q = max(3, min(data.num_questions or 5, 20))

    paper = llm_service.generate_assessment_paper(data.topic, difficulty=difficulty, num_questions=num_q)
    # Also generate structured questions so UI can render both printable paper and interactive quiz
    raw_questions = llm_service.generate_quiz_json(data.topic, num_questions=min(num_q, 5))
    questions = format_quiz_questions(raw_questions)

    return {
        "topic": data.topic,
        "difficulty": difficulty,
        "num_questions": num_q,
        "paper": paper,
        "questions": questions
    }

@router.post("/submit", response_model=QuizSubmitResponse)
def submit_quiz(data: QuizSubmitRequest):
    """Scores user quiz answers and provides instant performance feedback."""
    user_answers = data.answers or {}
    questions = data.questions or []

    correct_count = 0
    total = len(questions) if questions else len(user_answers)
    details = []

    for q in questions:
        q_id = str(q.id)
        chosen = user_answers.get(q_id, "").strip()
        is_correct = chosen.lower() == q.correct_answer.strip().lower()
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

    return {
        "total_questions": total,
        "correct_count": correct_count,
        "score_percentage": score_pct,
        "feedback": feedback,
        "details": details
    }
