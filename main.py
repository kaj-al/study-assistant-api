from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from database import engine, SessionLocal
from models import Base, User
from schemas import Signup, Login
from authen import hashPassword, verifyPassword, token
import os

load_dotenv()
client = ChatGroq(
    model="llama-3.1-8b-instant",
    api_key=os.getenv("GROQ_API_KEY"),
    max_tokens=1000,
)

app = FastAPI()

class Notes(BaseModel):
    text: str

class StudyPlan(BaseModel):
    topic: str
    days: int

@app.post("/signup")
def signup(user: Signup):
    db = SessionLocal()
    exist = db.query(User).filter(User.email == user.email).first()
    if exist:
        db.close()
        raise HTTPException(status_code=400, detail="Email already exists")
    hashed = hashPassword(user.password)
    new = User(name=user.name, email=user.email, password=hashed)
    db.add(new)
    db.commit()
    db.close()
    return {"message": "User created successfully"}

@app.post("/login")
def login(user: Login):
    db = SessionLocal()
    exist = db.query(User).filter(User.email == user.email).first()
    if not exist:
        db.close()
        raise HTTPException(status_code=401, detail="Email not exist")
    valid = verifyPassword(user.password, exist.password)
    db.close()
    if not valid:
        raise HTTPException(status_code=401, detail="Password not match")
    access = token(data={"sub": exist.email})
    return {"access_token": access, "token_type": "bearer"}

# helper to call the model
def generate_text(prompt: str) -> str:
    try:
        response = client.invoke([HumanMessage(content=prompt)])
        return response.content.strip()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/summarize")
def summarize(notes: Notes):
    prompt = (
        "Please summarize the following text into 2-3 short sentences:\n\n"
        f"{notes.text}"
    )
    summary = generate_text(prompt)
    return {"summary": summary}

@app.post("/quiz")
def generate_quiz(notes: Notes):
    prompt = (
        "Generate 3 quiz questions from the following given topic. "
        "Return each question with its correct answer in a simple list format.\n\n"
        f"{notes.text}"
    )
    quiz_text = generate_text(prompt)
    return {"quiz": quiz_text}

@app.post("/study-plan")
def plan(data: StudyPlan):
    prompt = (
        "Create a concise study plan for learning about the following topic in the given number of days. "
        "Return the plan as a short, day-by-day outline.\n\n"
        f"Topic: {data.topic}\nDays: {data.days}"
    )
    plan_text = generate_text(prompt)
    return {"topic": data.topic, "days": data.days, "plan": plan_text}

# tables
Base.metadata.create_all(bind=engine)

