from datetime import datetime , timedelta
from jose import jwt
from passlib.context import CryptContext
from dotenv import load_dotenv
import os

load_dotenv()

ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hashPassword(password:str):
    return pwd_context.hash(password)

def verifyPassword(plain,hashed):
    return pwd_context.verify(plain,hashed)

def token(data:dict):
    encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    encode.update({"exp":expire})
    secret = os.getenv("SECRET_KEY") or "changeme"
    alg = os.getenv("ALGORITHM") 
    encoded = jwt.encode(encode, secret, algorithm=alg)
    return encoded