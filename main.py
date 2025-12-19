import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from assistant.chain import assistant_chain

load_dotenv()

app = FastAPI(title="Vigneshwaran AI Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_ORIGIN")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AssistantRequest(BaseModel):
    message: str

class AssistantResponse(BaseModel):
    reply: str

@app.get("/")
def health_check():
    return {"status": "AI Assistant backend running"}

@app.post("/api/assistant", response_model=AssistantResponse)
async def assistant_endpoint(payload: AssistantRequest):
    message = payload.message.strip()

    if not message:
        raise HTTPException(status_code=400, detail="Message is required")

    try:
        reply = assistant_chain.invoke({
            "question": message
        })
        return {"reply": reply}
    except Exception as e:
        print("Assistant error:", e)
        raise HTTPException(status_code=500, detail="Internal server error")
