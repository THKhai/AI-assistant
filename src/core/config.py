import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = "deepseek-chat"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID", "0"))

VECTOR_BACKEND = os.getenv("VECTOR_BACKEND", "chroma")
CHROMA_PATH = str(BASE_DIR / "data" / "chroma_db")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = "personal_kb"

EMBED_MODEL = "BAAI/bge-small-en-v1.5"

SQLITE_PATH = str(BASE_DIR / "data" / "sqlite" / "app.db")
RAW_DATA_PATH = str(BASE_DIR / "data" / "raw")

CHUNK_SIZE = 512
CHUNK_OVERLAP = 64
RETRIEVAL_TOP_K = 5
CONVERSATION_HISTORY_TURNS = 5

JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "24"))

LOGIN_MAX_ATTEMPTS = int(os.getenv("LOGIN_MAX_ATTEMPTS", "5"))
LOGIN_LOCKOUT_MINUTES = int(os.getenv("LOGIN_LOCKOUT_MINUTES", "15"))

REFRESH_TOKEN_EXPIRY_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRY_DAYS", "30"))
TOTP_ISSUER = os.getenv("TOTP_ISSUER", "AI Assistant")

# "dev" = HTTP localhost, "prod" = HTTPS behind Cloudflare Tunnel
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")

# Optional: paths to TLS cert/key for local HTTPS (leave blank to use HTTP)
HTTPS_CERT_FILE = os.getenv("HTTPS_CERT_FILE", "")
HTTPS_KEY_FILE = os.getenv("HTTPS_KEY_FILE", "")
