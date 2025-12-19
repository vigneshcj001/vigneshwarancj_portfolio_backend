import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import traceback

from langchain_community.llms import Ollama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# --------------------------
# Load environment
# --------------------------
load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:120b-cloud")

if not OLLAMA_BASE_URL:
    raise RuntimeError("OLLAMA_BASE_URL is not set in .env")

os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY", "")
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT", "portfolio-assistant")

# --------------------------
# Prompt Template
# --------------------------
chat_prompt_template = ChatPromptTemplate.from_messages(
    [
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
        (
            "human",
            "{user_message}"
        ),
    ]
)

# --------------------------
# LLM & Chain
# --------------------------
ollama_llm = Ollama(
    base_url=OLLAMA_BASE_URL,
    model=OLLAMA_MODEL,
    temperature=0.6,
    num_predict=1024,  # increase for longer responses
)

output_parser = StrOutputParser()
assistant_chain = chat_prompt_template | ollama_llm | output_parser

# --------------------------
# FastAPI app
# --------------------------
app = FastAPI(title="Vigneshwaran Portfolio Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------
# API Models
# --------------------------
class AssistantRequest(BaseModel):
    message: str

class AssistantResponse(BaseModel):
    reply: str

# --------------------------
# Routes
# --------------------------
@app.get("/")
def health_check():
    return {"status": "Portfolio Assistant backend running"}

@app.post("/api/assistant", response_model=AssistantResponse)
async def assistant_endpoint(payload: AssistantRequest):
    user_message = payload.message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="Message is required")

    try:
        # Generate response
        reply = assistant_chain.invoke({"user_message": user_message})
        return {"reply": reply}

    except Exception as exc:
        # Print full traceback to console for debugging
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate assistant response: {str(exc)}"
        )
