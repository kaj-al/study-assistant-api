# AI Study API

An AI-powered FastAPI backend and study assistance.

## Base URL
http://127.0.0.1:8000

## Tech Stack
- FastAPI
- SQLite
- SQLAlchemy
- JWT Authentication
- Passlib/Bcrypt
- PyJWT
- Groq/Langchain

## Features
- User Signup
- User Login
- JWT Authentication
- AI notes summarization
- Quiz generation
- Study Plan
- Storage
- Swagger Documentation

## Installation
### Clone Repository
```bash 
git clone https://github.com/kaj-al/study-assistant-api.git
```

### Create Virtual Environment
```bash
python -m venv venv
```

### Activate Environment
- Windows
```bash
venv\Scripts\activate
```
-Mac/Linux
```bash
source venv/bin/activate
```
### Install requirements
```bash
pip install -r requirements.txt
```
## Run API
```bash
uvicorn main:app --reload
```
## Swagger Documentation
Open:
```bash
http://127.0.0.1:8000/docs
```
## ReDoc Documentation
Open:
```bash
http://127.0.0.1:8000/redoc
```
## Authentication
This API uses JWT based authentication.

## Endpoints
1. Home Route
- ```GET/```
```bash
{"message":"Running"}
```
2. User Signup
- ```POST/signup```
```bash
{
 "name":"xyz",
 "email":"xyz@gmail.com",
 "password":"123456"
}
```
```bash
{"message":"User created successfully"}
```
3. User Login
- ```POST/login``` 
```bash
{
 "email":"xyz@gmail.com",
 "password":"123456"
}
```
```bash
{
    "access_token":"jwt_token",
    "token_type":"bearer"
}
```
4. AI Text Summarization
- ```POST/summarize```

```bash
{
    "text":"AI is transforming education and learning systems."
}
```

```bash
{
    "summary":"AI is transforming education."
}
```
5. AI Generated quiz
- ```POST/quiz```

```bash
{
    "text":"AI is transforming education and learning systems."
}
```

```bash
{
    "summary":"AI is transforming education."
}
```

6. AI generated Study Plan
- ```POST/study-plan```

```bash
{
    "text":"AI is transforming education and learning systems."
}
```

```bash
{
    "summary":"AI is transforming education."
}
```

## DATABASE TABLES

### Users Table
|Column|Type|
|------|----|
|id |Integer|
|name|String|
|email|String|
|password|String|

### Notes Table
|Column|Type|
|------|----|
|id |Integer|
|content|String|
|summary|Text|

### History Table
|Column|Type|
|------|----|
|id |Integer|
|org_text|Text|
|summary|Text|

## Folder Structure

- main.py
- authen.py
- database.py
- models.py
- schemas.py
- requirements.txt
- .env
- test.db
- DOCUMENTATION.md

## JWT Authentication Flow

User Login -> Password Verification -> JWT Token Generation -> Protected API Access

## Security Features
- Password hashing with Bcrypt
- JWT Authentication
- Protected User Data
- Environment Variable Supoort

## Environment Variables
Create.env
```bash
SECRET_KEY=secret_key
GROQ_API_KEY=api_key
```

