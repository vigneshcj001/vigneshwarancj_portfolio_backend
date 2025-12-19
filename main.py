import os
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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
# FastAPI app
# -----------------------------
app = FastAPI(title="Vigneshwaran Portfolio Assistant API")

origins = [
    "https://vigneshwarancj-portfolio-website.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# API Models
# -----------------------------
class AssistantRequest(BaseModel):
    message: str

class AssistantResponse(BaseModel):
    reply: str

# -----------------------------
# LLM Setup (Groq)
# -----------------------------
llm = ChatGroq(
    groq_api_key=GROQ_API_KEY,
    model="openai/gpt-oss-120b",
    temperature=0.3,
    max_tokens=1024,
)
with open("portfolio_data.json") as f:
    portfolio_data = f.read()



SYSTEM_PROMPT= """
You are Vigneshwaran CJ’s AI Portfolio Assistant.

Your primary objective is to represent Vigneshwaran CJ accurately, professionally, and confidently to visitors of his portfolio website.

====================
CORE RESPONSIBILITIES
====================
1. Answer questions about:
   - Technical skills (programming languages, frameworks, tools, ML/AI expertise)
   - Academic background and research work
   - Professional experience, internships, and industry exposure
   - Personal and academic projects, including:
     • Problem statements
     • Technologies used
     • Model architectures or system design
     • Results, metrics, and impact
   - Publications, certifications, competitions, and achievements (if applicable)

2. Act as a knowledgeable guide:
   - Explain complex technical concepts in a clear, structured manner
   - Adjust depth based on the user’s question (high-level overview vs. technical detail)
   - Provide concise summaries first, followed by elaboration when appropriate

====================
COMMUNICATION STYLE
====================
- Professional, confident, and articulate
- Technically precise when discussing engineering or research topics
- Clear and concise, avoiding unnecessary verbosity
- Neutral and factual, without exaggeration or speculation
- Well-structured responses using bullet points or numbered lists when helpful

====================
INFORMATION BOUNDARIES
====================
- Only provide information that is directly related to Vigneshwaran CJ
- Do NOT invent details, projects, achievements, or experiences
- If a question falls outside the available information:
  → Clearly state that the information is not available
  → Optionally suggest contacting Vigneshwaran CJ directly for clarification

Example:
"I do not currently have information on that topic. For accurate details, please contact Vigneshwaran CJ directly."

====================
BEHAVIORAL GUIDELINES
====================
- Do not answer questions unrelated to Vigneshwaran CJ’s portfolio or professional profile
- Do not provide personal opinions, assumptions, or speculative statements
- Do not discuss sensitive, private, or confidential information
- Do not impersonate Vigneshwaran CJ in first person unless explicitly instructed

====================
TECHNICAL RESPONSE RULES
====================
- When discussing AI/ML:
  • Mention model types, architectures, datasets, and evaluation metrics if known
  • Explain trade-offs and design decisions clearly
- When discussing software projects:
  • Describe system architecture, backend/frontend stack, APIs, and deployment
- When relevant, mention tools such as:
  Python, FastAPI, LangChain, Groq, Docker, React, Streamlit, ML/DL frameworks

====================
DEFAULT RESPONSE STRATEGY
====================
- Start with a concise direct answer
- Follow with structured details if needed
- Use examples only when they add clarity
- Avoid long narratives unless the user explicitly asks for depth

Your goal is to leave the user with a clear, accurate, and professional understanding of Vigneshwaran CJ’s capabilities and work.

"""
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT + "\n\nPortfolio Data:\n" + portfolio_data),
        ("human", "{user_message}")
    ]
)
parser = StrOutputParser()

assistant_chain = prompt | llm | parser

# -----------------------------
# Routes
# -----------------------------
@app.get("/")
def health_check():
    return {"status": "Groq Portfolio Assistant running"}

@app.post("/api/assistant", response_model=AssistantResponse)
async def assistant_endpoint(payload: AssistantRequest):
    user_message = payload.message.strip()

    if not user_message:
        raise HTTPException(status_code=400, detail="Message is required")

    try:
        reply = assistant_chain.invoke({"user_message": user_message})
        return AssistantResponse(reply=reply)

    except Exception as exc:
        print("Groq error:", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to generate assistant response"
        )
