import os
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from starlette.middleware.base import BaseHTTPMiddleware

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# -----------------------------
# Load environment variables
# -----------------------------
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT")

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY not set in .env")

os.environ["LANGCHAIN_API_KEY"] = LANGCHAIN_API_KEY or ""
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = LANGCHAIN_PROJECT or "portfolio-assistant"

# -----------------------------
# Rate limiter
# -----------------------------
limiter = Limiter(key_func=get_remote_address, default_limits=["30/minute"])

# -----------------------------
# FastAPI app
# -----------------------------
app = FastAPI(
    title="Vigneshwaran Portfolio Assistant API",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# -----------------------------
# CORS — production origins only
# -----------------------------
ALLOWED_ORIGINS = [
    "https://vigneshwarancj-portfolio-website.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# -----------------------------
# Security headers middleware
# -----------------------------
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# -----------------------------
# Request size limit middleware
# -----------------------------
MAX_BODY_BYTES = 4096

class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_BODY_BYTES:
            return JSONResponse(status_code=413, content={"detail": "Request too large"})
        return await call_next(request)

app.add_middleware(RequestSizeLimitMiddleware)

# -----------------------------
# API Models
# -----------------------------
MAX_MESSAGE_LENGTH = 500

class AssistantRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=MAX_MESSAGE_LENGTH)

    @field_validator("message")
    @classmethod
    def sanitize_message(cls, v: str) -> str:
        return v.strip()

class AssistantResponse(BaseModel):
    reply: str

# -----------------------------
# Load portfolio data
# -----------------------------
with open("portfolio_data.json", "r", encoding="utf-8") as f:
    portfolio_data = f.read()

portfolio_data = portfolio_data.replace("{", "{{").replace("}", "}}")

# -----------------------------
# Output sanitizer
# -----------------------------
_FORBIDDEN = ["**", "*", "|", "#", "__", "~~"]

def clean_output(text: str) -> str:
    for token in _FORBIDDEN:
        text = text.replace(token, "")
    return text.strip()

# -----------------------------
# LLM Setup (Groq)
# -----------------------------
llm = ChatGroq(
    groq_api_key=GROQ_API_KEY,
    model="openai/gpt-oss-120b",
    temperature=0.3,
    max_tokens=1024,
)

SYSTEM_PROMPT = f"""
You are Vigneshwaran CJ's AI Portfolio Assistant.

Your role is to represent Vigneshwaran CJ accurately, professionally, and clearly to visitors of his portfolio website.

====================
CORE RESPONSIBILITIES
====================
- Answer questions about skills, projects, research, experience, and tools
- Explain technical topics clearly and concisely
- Adjust depth based on the user's question
- Only use information present in the portfolio data

====================
COMMUNICATION STYLE
====================
- Professional and factual
- Clear and structured
- Concise, without unnecessary verbosity
- Neutral and accurate

====================
INFORMATION BOUNDARIES
====================
- Do not invent or assume information
- If information is unavailable, state that clearly
- Do not provide personal opinions or speculation
- Do not impersonate Vigneshwaran CJ in first person

====================
OUTPUT FORMATTING RULES (STRICT)
====================
- Use plain text only
- Do not use tables
- Do not use markdown formatting
- Do not use bold, italics, headings, or symbols such as *, **, #, |, _
- Bullet points are allowed only using hyphens (-)
- Use line breaks for readability
- Keep responses suitable for a chat UI

Allowed example:
Skills overview:
- Programming languages: Python, JavaScript
- Backend frameworks: FastAPI, Node.js

Disallowed:
- Tables
- Markdown formatting
- Emphasis symbols

====================
DEFAULT RESPONSE STRATEGY
====================
- Start with a short, direct summary
- Follow with clean bullet points if listing items
- Avoid long paragraphs unless explicitly requested

Portfolio data:
{portfolio_data}
"""

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        ("human", "{user_message}"),
    ]
)

parser = StrOutputParser()
assistant_chain = prompt | llm | parser

# -----------------------------
# Routes
# -----------------------------
@app.get("/")
def health_check():
    return {"status": "ok"}

@app.post("/api/assistant", response_model=AssistantResponse)
@limiter.limit("10/minute")
async def assistant_endpoint(request: Request, payload: AssistantRequest):
    try:
        raw_reply = assistant_chain.invoke({"user_message": payload.message})
        reply = clean_output(raw_reply)
        return AssistantResponse(reply=reply)
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to generate response")
