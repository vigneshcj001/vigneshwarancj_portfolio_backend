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
# Comma-separated extra origins, e.g. "http://localhost:1234,http://127.0.0.1:4173"
# for local frontend development against this API.
EXTRA_ALLOWED_ORIGINS: list[str] = [
    origin.strip().rstrip("/")
    for origin in os.getenv("EXTRA_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]
ALLOWED_ORIGINS: list[str] = list(dict.fromkeys(filter(None, [
    "https://vigneshwarancj-portfolio-website.vercel.app",
    FRONTEND_ORIGIN,
    *EXTRA_ALLOWED_ORIGINS,
])))

# Number of reverse proxies in front of the API that append to X-Forwarded-For.
# 0 = use the socket peer address (safe default when exposed directly).
# Set to 1 on Render/Railway so each visitor gets their own rate-limit bucket.
TRUSTED_PROXY_COUNT: int = max(0, int(os.getenv("TRUSTED_PROXY_COUNT", "0") or 0))
GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
APP_VERSION: str = os.getenv("APP_VERSION", os.getenv("RENDER_GIT_COMMIT", "dev"))[:12]

MAX_BODY_BYTES: int = 65536
MAX_MESSAGE_LENGTH: int = 500
MAX_HISTORY_ITEMS: int = 8
MAX_HISTORY_CHARS: int = 1200
DATABASE_URL: str = os.getenv("DATABASE_URL", "")
ADMIN_API_KEY: str = os.getenv("ADMIN_API_KEY", "")
METADATA_CACHE_SECONDS: int = int(os.getenv("METADATA_CACHE_SECONDS", "3600"))
