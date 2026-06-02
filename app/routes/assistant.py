from fastapi import APIRouter, HTTPException, Request

from app.ai.chain import assistant_chain, build_history
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
        chat_history = build_history(
            [{"role": h.role, "content": h.content} for h in payload.history]
        )
        raw_reply = await assistant_chain.ainvoke(
            {
                "user_message": payload.message,
                "chat_history": chat_history,
            }
        )
        reply = clean_output(raw_reply)
        return AssistantResponse(reply=reply)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to generate response") from exc
