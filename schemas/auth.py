from pydantic import BaseModel
from typing import Optional, Dict, Any

class Signup(BaseModel):
    name: str
    email: str
    password: str

class Login(BaseModel):
    email: str
    password: str   

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Optional[Dict[str, Any]] = None

class AuthVerifyResponse(BaseModel):
    verified: bool
    user: Optional[Dict[str, Any]] = None
    email: Optional[str] = None
    message: Optional[str] = "Authentication successful"
