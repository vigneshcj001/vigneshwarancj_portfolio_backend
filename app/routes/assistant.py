import asyncio
import json
import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.ai.chain import assistant_chain, build_history
from app.ai.sanitizer import clean_output
from app.limiter import limiter
from app.models import AssistantRequest, AssistantResponse

logger = logging.getLogger(__name__)
router = APIRouter()

LLM_TIMEOUT_SECONDS = 30


@router.get("/")
def health_check():
    return {"status": "ok"}


@router.post("/api/assistant", response_model=AssistantResponse)
@limiter.limit("10/minute")
async def assistant_endpoint(request: Request, payload: AssistantRequest):
    try:
        chat_history = build_history(payload.history)
        raw_reply = await asyncio.wait_for(
            assistant_chain.ainvoke(
                {
                    "user_message": payload.message,
                    "chat_history": chat_history,
                }
            ),
            timeout=LLM_TIMEOUT_SECONDS,
        )
        reply = clean_output(raw_reply)
        return AssistantResponse(reply=reply)

    except asyncio.TimeoutError as exc:
        logger.warning("LLM timeout after %ss for message: %.60r", LLM_TIMEOUT_SECONDS, payload.message)
        raise HTTPException(status_code=504, detail="Response timed out — please try again.") from exc

    except Exception as exc:
        logger.exception("Unexpected error in assistant_endpoint: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to generate response") from exc


@router.post("/api/assistant/stream")
@limiter.limit("10/minute")
async def assistant_stream(request: Request, payload: AssistantRequest):
    """SSE streaming endpoint — emits text chunks as they arrive from the LLM."""
    chat_history = build_history(payload.history)

    async def generate():
        accumulated = ""
        try:
            async with asyncio.timeout(LLM_TIMEOUT_SECONDS):
                async for chunk in assistant_chain.astream(
                    {
                        "user_message": payload.message,
                        "chat_history": chat_history,
                    }
                ):
                    if chunk:
                        accumulated += chunk
                        yield f"data: {json.dumps({'text': chunk})}\n\n"

            # Send sanitized full text on done so frontend can replace
            cleaned = clean_output(accumulated)
            yield f"data: {json.dumps({'done': True, 'full': cleaned})}\n\n"

        except TimeoutError:
            logger.warning("Stream timeout for message: %.60r", payload.message)
            yield f"data: {json.dumps({'error': 'Response timed out — please try again.'})}\n\n"

        except Exception as exc:
            logger.exception("Streaming error: %s", exc)
            yield f"data: {json.dumps({'error': 'Failed to generate response.'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
