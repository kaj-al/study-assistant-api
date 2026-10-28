import os
import json
import logging
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional

import config

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are Nexora, an elite, encouraging AI study companion and academic tutor. "
    "Your goal is to explain concepts clearly, provide structured summaries, and help students master topics."
)

def call_groq(prompt: str, system: str = SYSTEM_PROMPT, max_tokens: int = 2000, temperature: float = 0.5) -> Optional[str]:
    api_key = config.GROQ_API_KEY
    if not api_key:
        return None
    models = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]
    for model in models:
        try:
            res = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens
                },
                timeout=12
            )
            if res.status_code == 200:
                data = res.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                if content and content.strip():
                    return content.strip()
        except Exception as e:
            logger.warning(f"Groq model {model} failed: {e}")
            continue
    return None

def call_openrouter(prompt: str, system: str = SYSTEM_PROMPT, max_tokens: int = 2000, temperature: float = 0.5) -> Optional[str]:
    api_key = config.OPENROUTER_API_KEY
    if not api_key:
        return None
    models = ["deepseek/deepseek-chat", "meta-llama/llama-3.1-8b-instruct", "openai/gpt-4o-mini", "google/gemini-2.5-flash"]
    for model in models:
        try:
            res = requests.post(
                config.OPENROUTER_BASE_URL or "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens
                },
                timeout=12
            )
            if res.status_code == 200:
                data = res.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                if content and content.strip():
                    return content.strip()
        except Exception as e:
            logger.warning(f"OpenRouter model {model} failed: {e}")
            continue
    return None

def generate_text(prompt: str, system: str = SYSTEM_PROMPT, max_tokens: int = 2000, temperature: float = 0.5) -> str:
    # 1. Try Groq (ultra fast)
    output = call_groq(prompt, system=system, max_tokens=max_tokens, temperature=temperature)
    if output:
        return output

    # 2. Try OpenRouter
    output = call_openrouter(prompt, system=system, max_tokens=max_tokens, temperature=temperature)
    if output:
        return output

    # 3. Fallback educational response
    return clean_asterisks(
        f"# Structured Overview\n\n"
        f"Core Subject: Key principles and foundations of the requested material.\n\n"
        f"Key Concepts:\n"
        f"- Fundamental theory and logical flow.\n"
        f"- Practical application in academic and real-world settings.\n"
        f"- Important takeaways for active recall and examination preparation.\n\n"
        f"Input Reference:\n{prompt[:350]}..."
    )

def clean_asterisks(text: str) -> str:
    """Removes annoying asterisks, double asterisks, and cleans formatting."""
    if not text:
        return ""
    import re
    # Convert leading bullet asterisks (* Item) to dash (- Item)
    text = re.sub(r'(?m)^\s*[\*•]\s+', '- ', text)
    # Remove all ** and * markers while preserving the words inside
    text = text.replace("**", "")
    text = text.replace("*", "")
    # Clean up accidental double spaces
    text = re.sub(r'[ \t]{2,}', ' ', text)
    return text.strip()

def generate_title_from_content(transcript: str, fallback_filename: str = "") -> str:
    """Infers a clean, specific academic topic title from lecture transcript."""
    if not transcript or len(transcript.strip()) < 10:
        return Path(fallback_filename).stem.replace("_", " ").title() if fallback_filename else "Video Lecture"
    
    prompt = (
        "Based on the following lecture transcript, generate a concise, highly specific academic title (3-7 words) "
        "that reflects the exact subject matter or problem discussed. Output ONLY the title, with no quotes or punctuation.\n\n"
        f"Transcript excerpt:\n{transcript[:3000]}"
    )
    title = generate_text(prompt, system="You are an expert academic titler. Output only the concise title.", max_tokens=30, temperature=0.2)
    cleaned = clean_asterisks(title).strip('"\':#\n ')
    if cleaned and len(cleaned) > 3 and not cleaned.lower().startswith(("structured", "lecture", "untitled")):
        return cleaned
    if fallback_filename:
        return Path(fallback_filename).stem.replace("_", " ").title()
    return "Video Lecture Notes"

def generate_summary(text: str) -> Dict[str, Any]:
    prompt = (
        "Analyze the following lecture/video transcript and extract the EXACT core information:\n"
        "1. A concise, comprehensive summary paragraph (3-5 sentences) summarizing specifically what was explained, demonstrated, or solved in this video.\n"
        "2. 4-6 specific key takeaways starting with a dash (-), detailing the actual principles, formulas, or conclusions taught.\n"
        "STRICT REQUIREMENTS:\n"
        "- Base every detail strictly on the provided content. NEVER use generic boilerplate or vague advice.\n"
        "- Mention real concepts, terminology, equations, or examples present in the lecture.\n"
        "- STRICT RULE: Do NOT use asterisks (** or *) anywhere in your output.\n\n"
        f"Source Content:\n{text[:25000]}"
    )
    result = generate_text(prompt, system="You are an expert academic tutor. Summarize strictly what is in the lecture without generic filler. Zero asterisks.", max_tokens=1500)
    result = clean_asterisks(result)
    lines = result.split("\n")
    summary_paragraph = []
    key_points = []
    for line in lines:
        cleaned = line.strip()
        if cleaned.startswith(("-", "•", "1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.")):
            point = clean_asterisks(cleaned.lstrip("-• 0123456789."))
            if point:
                key_points.append(point)
        elif cleaned and not cleaned.startswith("#"):
            cleaned_text = clean_asterisks(cleaned)
            if cleaned_text:
                summary_paragraph.append(cleaned_text)
    return {
        "summary": " ".join(summary_paragraph) if summary_paragraph else result[:400],
        "key_points": key_points[:6] if key_points else ["Core theoretical framework and mechanism", "Detailed principles and proofs covered", "Actionable revision checkpoints"]
    }

def generate_structured_notes(text: str) -> str:
    prompt = (
        "You are an elite academic tutor creating thorough, crystal-clear, exhaustive study notes from a video lecture transcript.\n\n"
        "CRITICAL REQUIREMENTS:\n"
        "1. EXTRACT EXACT INFORMATION: Extract every single important fact, concept, definition, equation, step-by-step workflow, and example mentioned in the lecture.\n"
        "2. NO GENERIC PLACEHOLDERS: Do NOT write generic filler like 'review core equations' or 'mastery requires comprehension'. Every bullet point MUST describe the ACTUAL topics, names, and specifics taught in the video.\n"
        "3. EXPLAIN SIMPLY & CLEARLY: Break down complex terminology into simple, intuitive explanations so any student can grasp it immediately.\n"
        "4. LANGUAGE: If the lecture was spoken in Hindi or Hinglish, explain the concepts clearly in English (or bilingual where appropriate) while preserving all original terminology and key terms.\n"
        "5. ZERO ASTERISKS: DO NOT use asterisks under any circumstances. Never use '**' for bold and never use '*' for italics or bullet points. Use clean dashes (-) or numbers (1, 2, 3) for lists.\n\n"
        "STRUCTURE TO FOLLOW:\n"
        "# [Exact Topic Name from Lecture]\n\n"
        "## Executive Summary\n"
        "(Explain the core subject matter, what problem it addresses, and the main conclusions in 3-4 clear sentences)\n\n"
        "## Core Concepts & Definitions\n"
        "- [Concept Name]: Specific, detailed explanation directly from the lecture without asterisks\n"
        "- [Concept Name]: Specific, detailed explanation directly from the lecture without asterisks\n\n"
        "## Detailed Step-by-Step Mechanisms & Workflows\n"
        "1. [First Step / Principle]: Full explanation of what happens and why\n"
        "2. [Second Step / Principle]: Full explanation of what happens and why\n\n"
        "## Concrete Examples, Calculations & Case Studies\n"
        "- Specific examples, numbers, equations, or scenarios explained by the speaker\n\n"
        "## Common Pitfalls & Critical Nuances\n"
        "- Nuances, distinctions, or caveats highlighted in the presentation\n\n"
        "## High-Yield Revision Points\n"
        "- Essential takeaway 1 for exams and practical mastery\n"
        "- Essential takeaway 2 for exams and practical mastery\n\n"
        f"Source Lecture Transcript:\n{text[:35000]}"
    )
    raw_notes = generate_text(
        prompt,
        system="You are an elite academic tutor who writes crystal-clear, exhaustive notes in clean plain text with zero asterisks, strictly reflecting the exact content taught in the lecture.",
        max_tokens=3500
    )
    return clean_asterisks(raw_notes)

def generate_quiz_json(text_or_topic: str, num_questions: int = 3) -> List[Dict[str, Any]]:
    prompt = (
        f"Generate {num_questions} multiple-choice quiz questions based strictly on the specific facts, terminology, formulas, and concepts explained in the following lecture material:\n\n"
        f"{text_or_topic[:20000]}\n\n"
        "CRITICAL RULES:\n"
        "1. Questions MUST test the EXACT information, definitions, techniques, and examples discussed in the text.\n"
        "2. Do NOT generate generic meta-questions like 'What is the primary objective?' or 'Which study method is most effective?'.\n"
        "3. Each question must have 4 plausible, distinct options (A, B, C, D) and exactly one correct answer matching one of the options.\n"
        "4. Include an informative explanation citing the reasoning from the lecture.\n\n"
        "Return strictly valid JSON with this exact structure and no other text or code fences:\n"
        "[\n"
        "  {\n"
        '    "id": 1,\n'
        '    "question": "Specific question testing real content from the lecture?",\n'
        '    "options": ["Option A", "Option B", "Option C", "Option D"],\n'
        '    "correct_answer": "Option A",\n'
        '    "explanation": "Why Option A is correct based on the lecture."\n'
        "  }\n"
        "]"
    )
    raw = generate_text(prompt, system="You are an expert exam creator. Output ONLY a valid JSON list with no markdown fences.", max_tokens=1500, temperature=0.2)
    # Parse JSON cleanly
    try:
        start_idx = raw.find("[")
        end_idx = raw.rfind("]")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            parsed = json.loads(raw[start_idx:end_idx + 1])
            if isinstance(parsed, list) and len(parsed) > 0:
                return parsed
    except Exception as e:
        logger.warning(f"Failed to parse quiz JSON: {e}")

    # Fallback questions based on content snippet
    snippet = clean_asterisks(text_or_topic[:80]).replace('"', '')
    return [
        {
            "id": 1,
            "question": f"Which key concept was central to the discussion in this lecture?",
            "options": [
                f"{snippet[:40]}",
                "Unrelated theoretical assumptions",
                "Hypothetical historical alternatives",
                "None of the above"
            ],
            "correct_answer": f"{snippet[:40]}",
            "explanation": "This concept forms the foundational subject matter addressed in the lecture."
        },
        {
            "id": 2,
            "question": "How are the primary mechanisms in this lecture systematically applied?",
            "options": [
                "Through step-by-step methodology and practical verification",
                "By random trial and error without structure",
                "By ignoring foundational principles",
                "Exclusively through passive memorization"
            ],
            "correct_answer": "Through step-by-step methodology and practical verification",
            "explanation": "The lecture emphasizes methodical application and analytical rigor."
        },
        {
            "id": 3,
            "question": "What is the critical takeaway for problem-solving emphasized in the material?",
            "options": [
                "Understanding the underlying rules and avoiding common pitfalls",
                "Skipping validation and edge cases",
                "Focusing only on surface terminology",
                "Relying solely on intuition without proof"
            ],
            "correct_answer": "Understanding the underlying rules and avoiding common pitfalls",
            "explanation": "Mastery requires deep awareness of edge cases, rules, and core proofs."
        }
    ]

def generate_study_plan(topic: str, days: int = 7, level: str = "Intermediate") -> str:
    prompt = (
        f"Create an optimal, day-by-day study roadmap for mastering '{topic}' in {days} days at the {level} level.\n\n"
        "Format using Markdown:\n"
        f"# {days}-Day Study Roadmap: {topic} ({level})\n"
        "### Overview & Learning Objectives\n\n"
        "For each day, specify:\n"
        "- **Day X: [Theme / Focus]**\n"
        "  - 🎯 Goal:\n"
        "  - 📖 Recommended Study Topics:\n"
        "  - ⚡ Practical Exercises / Practice Tasks:\n"
        "  - ⏱️ Target Time: (e.g. 2 hours)\n\n"
        "End with **Final Revision & Self-Assessment Checklist** and 5 practice questions."
    )
    return generate_text(prompt, system="You are an expert curriculum designer and academic coach.", max_tokens=2500)

def generate_assessment_paper(topic: str, difficulty: str = "Medium", num_questions: int = 5) -> str:
    prompt = (
        f"Generate a rigorous, crystal-clear, formal academic examination and assessment paper on '{topic}'.\n"
        f"Academic Level: {difficulty}.\n"
        f"Total Questions: {num_questions} core examination questions.\n\n"
        "STRUCTURE TO FOLLOW STRICTLY:\n"
        "# DEPARTMENT OF ACADEMIC EXAMINATIONS & ASSESSMENT\n"
        f"## Formal Examination Paper: {topic.title()}\n"
        f"Time Allowed: 90 Minutes | Total Marks: 100 Marks | Academic Level: {difficulty}\n\n"
        "### General Instructions to Candidates\n"
        "1. All questions in Section A (Objective) and Section B (Analytical) are mandatory.\n"
        "2. Marks allocation for each individual question is specified in brackets [Marks].\n"
        "3. Write answers with clear logical steps, explicit assumptions, and diagrams where required.\n\n"
        "## Section A: Multiple-Choice Conceptual Mastery [30 Marks]\n"
        "(Provide 3-5 challenging multiple-choice questions testing core principles, definitions, and edge cases. List 4 distinct options A, B, C, D for each question)\n\n"
        "## Section B: Short Analytical & Theoretical Problems [35 Marks]\n"
        "(Provide 2-3 focused conceptual problem questions requiring definitions, proof sketches, or comparative analysis with clear marks [10M / 15M])\n\n"
        "## Section C: Comprehensive Problem Solving & Case Study [35 Marks]\n"
        "(Provide an in-depth numerical, mathematical, algorithmic, or practical architectural scenario problem with sub-parts a, b, c)\n\n"
        "---\n\n"
        "## Official Marking Scheme & Model Solutions\n"
        "### Section A Answer Key & Explanations\n"
        "- Question 1: Correct Option - Detailed academic reasoning\n"
        "- Question 2: Correct Option - Detailed academic reasoning\n\n"
        "### Section B & C Model Answers & Scoring Rubrics\n"
        "- Step-by-step scoring criteria explaining how full and partial credit is awarded\n\n"
        "CRITICAL FORMATTING:\n"
        "- DO NOT use asterisks under any circumstances. Never use '**' or '*'.\n"
        "- Use clean plain text with standard markdown headings (# Title, ## Section, ### Subtopic) and clean dashes (-).\n"
        "- Ensure every question is rigorous, unambiguous, and testing authentic conceptual mastery."
    )
    raw = generate_text(prompt, system="You are a distinguished university professor and academic examination director who prepares flawless, crystal-clear examination papers with zero asterisks.", max_tokens=3500)
    return clean_asterisks(raw)

def tutor_chat_coach(user_message: str, history: List[Dict[str, str]], language: str = "English") -> str:
    system = (
        "You are Nexora, an elite, highly encouraging, interactive AI Learning Coach and academic tutor.\n"
        "Your pedagogical approach:\n"
        "1. Clarify doubts directly and concisely using an intuitive, real-world analogy.\n"
        "2. Break down complex steps into clean, readable points.\n"
        "3. Conclude with ONE multiple-choice check question (labeled Question, with 4 distinct options: A, B, C, D) to verify student understanding and encourage active recall.\n"
        "4. If the student answers your question or gets it right, praise them and advance the topic.\n"
        "5. If they get it wrong, gently explain why and simplify the concept.\n"
        "6. Do NOT use markdown asterisks (no '**' or '*'). Use clean capitalization, headers, and dashes (-).\n"
        f"Respond in {language}."
    )
    context_msgs = []
    for h in history[-8:]:
        role_label = "Student" if h.get("role") == "user" else "Nexora Tutor"
        context_msgs.append(f"{role_label}: {h.get('content', '')}")
    context_str = "\n".join(context_msgs)
    prompt = f"{context_str}\n\nStudent: {user_message}\nNexora Tutor:"
    raw = generate_text(prompt, system=system, max_tokens=1200, temperature=0.4)
    return clean_asterisks(raw)
