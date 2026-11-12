import asyncio
import hashlib
import json
import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, StreamingResponse

from app.ai.chain import assistant_chain, build_history
from app.ai.okf import knowledge_version
from app.agent.graph import AgentTurn, run_agent_turn, stream_agent_turn
from app.agent.memory import delete_memory, load_memory, save_memory
from app.config import ANSWER_CACHE_DAYS
from app.services.storage import get_cached_answer, save_cached_answer
from app.ai.presentation import LANGUAGE_NAMES, answer_status
from app.ai.sanitizer import clean_output
from app.limiter import limiter
from app.models import AssistantRequest, AssistantResponse, HistoryItem

logger = logging.getLogger(__name__)
router = APIRouter()

LLM_TIMEOUT_SECONDS = 30
BUSY_MESSAGE = "The assistant is busy right now — please try again in a minute."
_response_cache: dict[tuple[str, str], dict] = {}


def _normalize_question(message: str) -> str:
    return " ".join(message.casefold().split()).rstrip("?!. ")


def _cache_key(payload: AssistantRequest, raw_history: list[dict[str, str]]) -> str | None:
    """Only opening questions are cached: follow-ups depend on conversation context.

    The knowledge version is part of the key, so editing the Markdown knowledge
    base invalidates every cached answer without manual cleanup.
    """
    if raw_history:
        return None
    material = f"{knowledge_version()}|{payload.language}|{_normalize_question(payload.message)}"
    return hashlib.sha256(material.encode()).hexdigest()


async def _cached(key: str | None) -> dict | None:
    if key is None:
        return None
    if key in _response_cache:
        return _response_cache[key]
    try:
        stored = await get_cached_answer(key, ANSWER_CACHE_DAYS)
    except Exception:
        logger.warning("Answer cache read failed", exc_info=True)
        return None
    if stored and isinstance(stored.get("reply"), str):
        _remember_locally(key, stored)
        return stored
    return None


def _remember_locally(key: str, value: dict) -> None:
    if len(_response_cache) >= 256:
        _response_cache.pop(next(iter(_response_cache)))
    _response_cache[key] = value


async def _remember(key: str | None, value: dict) -> None:
    if key is None:
        return
    shared = {**value, "session_id": None}  # never share one visitor's session ID
    _remember_locally(key, shared)
    try:
        await save_cached_answer(key, shared)
    except Exception:
        logger.warning("Answer cache write failed", exc_info=True)


def _is_capacity_error(exc: Exception) -> bool:
    """True for Groq 413 (request too large) / 429 (rate limit) responses."""
    status = getattr(exc, "status_code", None)
    if status in (413, 429):
        return True
    text = str(exc).lower()
    return "rate_limit" in text or "request too large" in text


async def _history(payload: AssistantRequest) -> tuple[list[HistoryItem], list[dict[str, str]]]:
    stored = await load_memory(payload.session_id)
    raw = stored or [{"role": item.role, "content": item.content} for item in payload.history]
    # Apply the same history budget to restored sessions as client payloads.
    items = AssistantRequest.cap_history([HistoryItem.model_validate(item) for item in raw])
    return items, [{"role": item.role, "content": item.content} for item in items]


def _metadata(turn: AgentTurn, session_id: str | None) -> dict:
    return {
        "sources": list(turn.sources),
        "followups": list(turn.followups),
        "project": turn.project,
        "actions": [action.model_dump() for action in turn.actions],
        "tools": [trace.model_dump() for trace in turn.tool_trace],
        "session_id": session_id,
    }


async def _persist(payload: AssistantRequest, history: list[dict[str, str]], reply: str) -> None:
    await save_memory(payload.session_id, [
        *history,
        {"role": "user", "content": payload.message},
        {"role": "assistant", "content": reply},
    ])


@router.get("/")
def health_check():
    return {"status": "ok"}


@router.delete("/api/assistant/session/{session_id}", status_code=204)
@limiter.limit("20/minute")
async def delete_session(request: Request, session_id: str):
    """Erase a conversation's server-side history.

    The session ID is a random value only the visitor's browser holds, so it acts
    as the capability to delete. Unknown IDs also return 204 so the endpoint
    cannot be used to discover which sessions exist.
    """
    if not await delete_memory(session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID")
    return Response(status_code=204)


@router.post("/api/assistant", response_model=AssistantResponse)
@limiter.limit("100/day")
@limiter.limit("10/minute")
async def assistant_endpoint(request: Request, payload: AssistantRequest):
    try:
        history_items, raw_history = await _history(payload)
        key = _cache_key(payload, raw_history)
        cached = await _cached(key)
        if cached:
            await _persist(payload, raw_history, cached["reply"])
            return AssistantResponse(**{**cached, "session_id": payload.session_id})
        turn = await run_agent_turn(payload.message, raw_history, payload.language, payload.session_id)
        metadata = _metadata(turn, payload.session_id)
        if turn.direct_reply:
            response = {"reply": turn.direct_reply, **metadata}
            await _persist(payload, raw_history, turn.direct_reply)
            await _remember(key, response)
            return AssistantResponse(**response)
        chat_history = build_history(history_items)
        raw_reply = await asyncio.wait_for(
            assistant_chain.ainvoke(
                {
                    "user_message": payload.message,
                    "chat_history": chat_history,
                    "knowledge_context": turn.knowledge_context,
                    "target_language": LANGUAGE_NAMES[payload.language],
                },
                config={"run_name": "portfolio-grounded-answer", "tags": ["portfolio", "groq"], "metadata": {"session_id": payload.session_id or "ephemeral"}},
            ),
            timeout=LLM_TIMEOUT_SECONDS,
        )
        reply = clean_output(raw_reply)
        response = {"reply": reply, **metadata}
        await _persist(payload, raw_history, reply)
        await _remember(key, response)
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
            history_items, raw_history = await _history(payload)
            key = _cache_key(payload, raw_history)
            cached = await _cached(key)
            if cached:
                metadata = {name: cached.get(name, default) for name, default in (
                    ("sources", []), ("followups", []), ("project", None),
                    ("actions", []), ("tools", []),
                )}
                # Record the turn so follow-up questions keep their context.
                await _persist(payload, raw_history, cached["reply"])
                yield f"data: {json.dumps({'type': 'done', 'done': True, 'full': cached['reply'], 'cached': True, 'session_id': payload.session_id, **metadata})}\n\n"
                return
            turn = None
            async for event in stream_agent_turn(payload.message, raw_history, payload.language, payload.session_id):
                if await request.is_disconnected():
                    return
                if isinstance(event, AgentTurn):
                    turn = event
                else:
                    yield f"data: {json.dumps(event)}\n\n"
            if turn is None:
                raise RuntimeError("Portfolio turn did not complete")
            metadata = _metadata(turn, payload.session_id)
            for action in turn.actions:
                yield f"data: {json.dumps({'type': 'ui_action', 'action': action.model_dump()})}\n\n"
            if turn.direct_reply:
                response = {"reply": turn.direct_reply, **metadata}
                await _persist(payload, raw_history, turn.direct_reply)
                await _remember(key, response)
                yield f"data: {json.dumps({'type': 'done', 'done': True, 'full': turn.direct_reply, **metadata})}\n\n"
                return
            chat_history = build_history(history_items)
            yield f"data: {json.dumps({'type': 'status', 'phase': 'answering', 'message': answer_status(payload.message, turn.project)})}\n\n"
            async with asyncio.timeout(LLM_TIMEOUT_SECONDS):
                async for chunk in assistant_chain.astream(
                    {
                        "user_message": payload.message,
                        "chat_history": chat_history,
                        "knowledge_context": turn.knowledge_context,
                        "target_language": LANGUAGE_NAMES[payload.language],
                    },
                    config={"run_name": "portfolio-grounded-answer-stream", "tags": ["portfolio", "groq", "stream"], "metadata": {"session_id": payload.session_id or "ephemeral"}},
                ):
                    if chunk:
                        if await request.is_disconnected():
                            return
                        accumulated += chunk
                        yield f"data: {json.dumps({'type': 'token', 'text': chunk})}\n\n"

            # Send sanitized full text on done so frontend can replace
            cleaned = clean_output(accumulated)
            response = {"reply": cleaned, **metadata}
            await _persist(payload, raw_history, cleaned)
            await _remember(key, response)
            yield f"data: {json.dumps({'type': 'done', 'done': True, 'full': cleaned, **metadata})}\n\n"

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
