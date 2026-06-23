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
