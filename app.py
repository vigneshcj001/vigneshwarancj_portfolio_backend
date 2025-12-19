import os
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from langchain_community.llms import Ollama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# -----------------------------
# Load environment variables
# -----------------------------
load_dotenv()

os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY")
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")

if not OLLAMA_BASE_URL or not OLLAMA_MODEL:
    raise RuntimeError("OLLAMA_BASE_URL or OLLAMA_MODEL not set in .env")

# -----------------------------
# FastAPI app
# -----------------------------
app = FastAPI(title="Vigneshwaran Portfolio Assistant API")

# Allow only the deployed frontend
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
# LLM Setup
# -----------------------------
chat_prompt_template = ChatPromptTemplate.from_messages([
    (
        "system",
        """
You are Vigneshwaran CJ's AI portfolio assistant.

Your role:
- Answer questions about Vigneshwaran's skills, projects, research, and experience
- Be professional, concise, and confident
- If a question is outside his background, politely say you do not have that information
"""
    ),
    ("human", "{user_message}")
])

ollama_llm = Ollama(
    base_url=OLLAMA_BASE_URL,
    model=OLLAMA_MODEL,
    temperature=0.6,
    num_predict=512
)

output_parser = StrOutputParser()
assistant_chain = chat_prompt_template | ollama_llm | output_parser

# -----------------------------
# Routes
# -----------------------------
@app.get("/")
def health_check():
    return {"status": "Portfolio Assistant backend running"}

@app.post("/api/assistant", response_model=AssistantResponse)
async def assistant_endpoint(payload: AssistantRequest):
    user_message = payload.message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="Message is required")

    try:
        reply = assistant_chain.invoke({"user_message": user_message})
        return {"reply": reply}
    except Exception as exc:
        print("Assistant error:", exc)
        raise HTTPException(status_code=500, detail="Failed to generate assistant response")
