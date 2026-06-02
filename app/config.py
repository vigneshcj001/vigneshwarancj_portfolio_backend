import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
LANGCHAIN_API_KEY: str = os.getenv("LANGCHAIN_API_KEY", "")
LANGCHAIN_PROJECT: str = os.getenv("LANGCHAIN_PROJECT", "portfolio-assistant")

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY not set in environment")

os.environ["LANGCHAIN_API_KEY"] = LANGCHAIN_API_KEY
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = LANGCHAIN_PROJECT

ALLOWED_ORIGINS: list[str] = [
    "https://vigneshwarancj-portfolio-website.vercel.app",
]

MAX_BODY_BYTES: int = 4096
MAX_MESSAGE_LENGTH: int = 500
