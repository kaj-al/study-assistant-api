import os
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "").strip()
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "").strip()
SECRET_KEY = os.getenv("SECRET_KEY", "6bf247ddfd825ef0257db3dcf8504b79c01617b2dd83809d6ec1ade5e53cbe7d").strip()
ALGORITHM = os.getenv("ALGORITHM", "HS256").strip()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db").strip()
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1/chat/completions").strip()
MAX_UPLOAD_MB = 100
MAX_YOUTUBE_MINUTES = 60
