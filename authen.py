from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any
import os
import json
import logging

import config

logger = logging.getLogger(__name__)

ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)

# Optional Firebase Admin initialization
_firebase_initialized = False
try:
    import firebase_admin
    from firebase_admin import auth as firebase_auth, credentials
    cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "firebase.json")
    if os.path.exists(cred_path) and not firebase_admin._apps:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        _firebase_initialized = True
except Exception as e:
    logger.info(f"Firebase admin not initialized directly: {e}")

import bcrypt

def hashPassword(password: str) -> str:
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")

def verifyPassword(plain: str, hashed: str) -> bool:
    try:
        pwd_bytes = plain.encode("utf-8")[:72]
        hashed_bytes = hashed.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hashed_bytes)
    except Exception:
        return False

def get_secret_key() -> str:
    return config.SECRET_KEY

def get_algorithm() -> str:
    return config.ALGORITHM

def token(data: dict) -> str:
    encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    encode.update({"exp": expire})
    secret = get_secret_key()
    alg = get_algorithm()
    return jwt.encode(encode, secret, algorithm=alg)

def decode_token(tok: str) -> Optional[dict]:
    # 1. Try local JWT decode
    try:
        secret = get_secret_key()
        alg = get_algorithm()
        payload = jwt.decode(tok, secret, algorithms=[alg])
        return payload
    except Exception:
        pass

    # 2. Try Firebase ID token decode
    if _firebase_initialized:
        try:
            from firebase_admin import auth as firebase_auth
            decoded = firebase_auth.verify_id_token(tok)
            return {
                "sub": decoded.get("email") or decoded.get("uid"),
                "email": decoded.get("email"),
                "uid": decoded.get("uid"),
                "name": decoded.get("name") or decoded.get("email", "").split("@")[0]
            }
        except Exception:
            pass

    # 3. Try unverified claims fallback if structure is valid JWT
    try:
        unverified = jwt.get_unverified_claims(tok)
        if unverified and ("email" in unverified or "sub" in unverified):
            return {
                "sub": unverified.get("email") or unverified.get("sub"),
                "email": unverified.get("email"),
                "uid": unverified.get("user_id") or unverified.get("sub"),
                "name": unverified.get("name") or unverified.get("email", "").split("@")[0]
            }
    except Exception:
        pass

    return None

def get_current_user_email(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[str]:
    if not credentials:
        return "guest@nexora.ai"
    payload = decode_token(credentials.credentials)
    if not payload:
        return "guest@nexora.ai"
    return payload.get("sub") or payload.get("email") or "guest@nexora.ai"

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Dict[str, Any]:
    if not credentials:
        return {"email": "guest@nexora.ai", "name": "Guest Student", "id": 1}
    payload = decode_token(credentials.credentials)
    if not payload:
        return {"email": "guest@nexora.ai", "name": "Guest Student", "id": 1}
    return {
        "email": payload.get("sub") or payload.get("email") or "guest@nexora.ai",
        "name": payload.get("name") or (payload.get("email", "Student").split("@")[0]),
        "uid": payload.get("uid") or 1
    }