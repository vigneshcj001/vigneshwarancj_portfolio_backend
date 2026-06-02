from fastapi import APIRouter, HTTPException, Request

from app.ai.chain import assistant_chain
from app.ai.sanitizer import clean_output
from app.limiter import limiter
from app.models import AssistantRequest, AssistantResponse

router = APIRouter()


@router.get("/")
def health_check():
    return {"status": "ok"}


@router.post("/api/assistant", response_model=AssistantResponse)
@limiter.limit("10/minute")
async def assistant_endpoint(request: Request, payload: AssistantRequest):
    try:
        raw_reply = assistant_chain.invoke({"user_message": payload.message})
        reply = clean_output(raw_reply)
        return AssistantResponse(reply=reply)
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to generate response")
