import os
import re
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

FRONTEND = os.getenv("FRONTEND_ORIGIN", "http://127.0.0.1:1234")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11501")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "deepseek-r1:1.5b")

app = FastAPI(title="Vigneshwaran Portfolio AI Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND, "http://localhost:1234", "http://127.0.0.1:1234"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Message(BaseModel):
    message: str


def clean_reply(raw: str) -> str:
    """Remove DeepSeek reasoning, Answer:, undefined, and junk."""
    if not raw:
        return ""

    text = raw

    # Remove <think>...</think> blocks
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)

    # Remove lines starting with think>
    text = re.sub(r"^\s*think>.*?$", "", text, flags=re.MULTILINE | re.IGNORECASE)

    # Remove leading "Answer:" prefix if present
    text = re.sub(r"^\s*Answer:\s*", "", text, flags=re.IGNORECASE)

    # Remove any standalone 'undefined'
    text = re.sub(r"\bundefined\b", "", text, flags=re.IGNORECASE)

    # Collapse excessive blank lines and trim
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    return text


SYSTEM_PROMPT = """
You are Vigneshwaran C. J.'s personal AI assistant.
You MUST ONLY answer questions about:

• His skills:
  AI/ML, Generative AI, Deep Learning, RAG, LangChain, Agentic AI,
  Computational Glycobiology, Bioinformatics, Network Science,
  Data Science, NLP, Computer Vision.

• His tech stack:
  Python, R, SQL, PyTorch, TensorFlow, NumPy, Pandas, Cytoscape,
  React.js, Node.js, FastAPI, Flask, MongoDB, PostgreSQL, AWS,
  Tailwind CSS, GitHub, Docker, REST APIs.

• His projects:
  Syncly (professional networking platform),
  GlycanBench (AI-assisted glycomics analysis),
  CJBot, CJFoods AI Webapp, portfolio systems, ML pipelines.

• His research interests:
  Glycobiology, explainable ML, glycomics, Big Data Biology,
  AI models for biological systems, computational drug design.

RULES:
1. Do NOT reveal internal reasoning or chain-of-thought.
2. If the question is unrelated to Vigneshwaran, reply exactly:
   "I can only answer questions about Vigneshwaran C. J., his skills, research, and projects."
3. Be concise, professional, and factual.
"""


@app.get("/")
def health():
    return {"status": "Backend running with DeepSeek via Ollama"}


@app.post("/api/assistant")
def assistant(msg: Message):
    user_msg = msg.message.strip()
    if not user_msg:
        raise HTTPException(status_code=400, detail="Message must not be empty")

    # Local debug shortcut
    if user_msg.lower().startswith("local-test"):
        return {"reply": "Local backend OK — no AI call made."}

    try:
        resp = requests.post(
            f"{OLLAMA_URL}/v1/chat/completions",
            json={
                "model": OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                "stream": False,
            },
            timeout=180,
        )
    except Exception as e:
        print("Ollama connection error:", e)
        raise HTTPException(status_code=500, detail="Could not reach Ollama")

    if resp.status_code != 200:
        print("Ollama returned error:", resp.status_code, resp.text)
        raise HTTPException(status_code=500, detail="AI Model Error")

    data = resp.json()

    try:
        raw_reply = data["choices"][0]["message"]["content"]
    except Exception as e:
        print("Bad response structure from Ollama:", e, data)
        raise HTTPException(status_code=500, detail="Invalid AI response")

    reply = clean_reply(raw_reply)

    if not reply:
        reply = "That detail isn't available in the portfolio."

    return {"reply": reply}
