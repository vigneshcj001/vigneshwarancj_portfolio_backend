import os
from pathlib import Path
from dotenv import load_dotenv

WORKSPACE_ENV = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(WORKSPACE_ENV)

GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
LAYA_API_KEY: str = os.getenv("LAYA_API_KEY", "")
LAYA_BASE_URL: str = os.getenv(
    "LAYA_BASE_URL", "https://laya-production-b57e.up.railway.app"
).rstrip("/")
LAYA_TIMEOUT_SECONDS: float = float(os.getenv("LAYA_TIMEOUT_SECONDS", "8"))
LANGCHAIN_API_KEY: str = os.getenv("LANGCHAIN_API_KEY", "")
LANGCHAIN_PROJECT: str = os.getenv("LANGCHAIN_PROJECT", "portfolio-assistant")

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY not set in environment")

# Only enable LangSmith tracing when an API key is explicitly provided.
# Leaving tracing on without a key adds latency and logs user conversations
# to LangChain servers unintentionally.
if LANGCHAIN_API_KEY and os.getenv("LANGCHAIN_TRACING_V2", "true").casefold() != "false":
    os.environ["LANGCHAIN_API_KEY"] = LANGCHAIN_API_KEY
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = LANGCHAIN_PROJECT

FRONTEND_ORIGIN: str = os.getenv("FRONTEND_ORIGIN", "").rstrip("/")
ALLOWED_ORIGINS: list[str] = list(dict.fromkeys(filter(None, [
    "https://vigneshwarancj-portfolio-website.vercel.app",
    FRONTEND_ORIGIN,
])))

MAX_BODY_BYTES: int = 65536
MAX_MESSAGE_LENGTH: int = 500
MAX_HISTORY_ITEMS: int = 8
MAX_HISTORY_CHARS: int = 1200
DATABASE_URL: str = os.getenv("DATABASE_URL", "")
ADMIN_API_KEY: str = os.getenv("ADMIN_API_KEY", "")
METADATA_CACHE_SECONDS: int = int(os.getenv("METADATA_CACHE_SECONDS", "3600"))
