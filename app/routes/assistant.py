import asyncio
import json
import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.ai.chain import assistant_chain, build_history
from app.ai.orchestrator import prepare_turn
from app.ai.presentation import LANGUAGE_NAMES, response_metadata
from app.ai.sanitizer import clean_output
from app.limiter import limiter
from app.models import AssistantRequest, AssistantResponse

logger = logging.getLogger(__name__)
router = APIRouter()

LLM_TIMEOUT_SECONDS = 30
BUSY_MESSAGE = "The assistant is busy right now — please try again in a minute."
_response_cache: dict[tuple[str, str], dict] = {}


def _cache_key(payload: AssistantRequest) -> tuple[str, str] | None:
    return None if payload.history else (payload.language, payload.message.casefold())


def _remember(key: tuple[str, str] | None, value: dict) -> None:
    if key is None:
        return
    if len(_response_cache) >= 256:
        _response_cache.pop(next(iter(_response_cache)))
    _response_cache[key] = value


def _is_capacity_error(exc: Exception) -> bool:
    """True for Groq 413 (request too large) / 429 (rate limit) responses."""
    status = getattr(exc, "status_code", None)
    if status in (413, 429):
        return True
    text = str(exc).lower()
    return "rate_limit" in text or "request too large" in text


@router.get("/")
def health_check():
    return {"status": "ok"}


@router.post("/api/assistant", response_model=AssistantResponse)
@limiter.limit("100/day")
@limiter.limit("10/minute")
async def assistant_endpoint(request: Request, payload: AssistantRequest):
    try:
        key = _cache_key(payload)
        if key in _response_cache:
            return AssistantResponse(**_response_cache[key])
        prepared = await prepare_turn(payload.message, payload.history, payload.language)
        metadata = response_metadata(prepared)
        if prepared.direct_reply:
            response = {"reply": prepared.direct_reply, **metadata}
            _remember(key, response)
            return AssistantResponse(**response)
        chat_history = build_history(payload.history)
        raw_reply = await asyncio.wait_for(
            assistant_chain.ainvoke(
                {
                    "user_message": payload.message,
                    "chat_history": chat_history,
                    "knowledge_context": prepared.knowledge_context,
                    "target_language": LANGUAGE_NAMES[payload.language],
                }
            ),
            timeout=LLM_TIMEOUT_SECONDS,
        )
        reply = clean_output(raw_reply)
        response = {"reply": reply, **metadata}
        _remember(key, response)
        return AssistantResponse(**response)

    except asyncio.TimeoutError as exc:
        logger.warning("LLM timeout after %ss for message: %.60r", LLM_TIMEOUT_SECONDS, payload.message)
        raise HTTPException(status_code=504, detail="Response timed out — please try again.") from exc

    except Exception as exc:
        if _is_capacity_error(exc):
            logger.warning("LLM capacity error: %s", exc)
            raise HTTPException(status_code=503, detail=BUSY_MESSAGE) from exc
        logger.exception("Unexpected error in assistant_endpoint: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to generate response") from exc


@router.post("/api/assistant/stream")
@limiter.limit("100/day")
@limiter.limit("10/minute")
async def assistant_stream(request: Request, payload: AssistantRequest):
    """SSE streaming endpoint — emits text chunks as they arrive from the LLM."""

    async def generate():
        accumulated = ""
        try:
            key = _cache_key(payload)
            if key in _response_cache:
                cached = _response_cache[key]
                yield f"data: {json.dumps({'done': True, 'full': cached['reply'], **{name: cached[name] for name in ('sources', 'followups', 'project')}})}\n\n"
                return
            prepared = await prepare_turn(payload.message, payload.history, payload.language)
            metadata = response_metadata(prepared)
            if prepared.direct_reply:
                response = {"reply": prepared.direct_reply, **metadata}
                _remember(key, response)
                yield f"data: {json.dumps({'done': True, 'full': prepared.direct_reply, **metadata})}\n\n"
                return
            chat_history = build_history(payload.history)
            async with asyncio.timeout(LLM_TIMEOUT_SECONDS):
                async for chunk in assistant_chain.astream(
                    {
                        "user_message": payload.message,
                        "chat_history": chat_history,
                        "knowledge_context": prepared.knowledge_context,
                        "target_language": LANGUAGE_NAMES[payload.language],
                    }
                ):
                    if chunk:
                        if await request.is_disconnected():
                            return
                        accumulated += chunk
                        yield f"data: {json.dumps({'text': chunk})}\n\n"

            # Send sanitized full text on done so frontend can replace
            cleaned = clean_output(accumulated)
            response = {"reply": cleaned, **metadata}
            _remember(key, response)
            yield f"data: {json.dumps({'done': True, 'full': cleaned, **metadata})}\n\n"

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
