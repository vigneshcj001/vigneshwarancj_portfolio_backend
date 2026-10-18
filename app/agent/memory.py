import re
from collections import OrderedDict

from app.services.storage import load_agent_session, save_agent_session

_SESSION_RE = re.compile(r"^[A-Za-z0-9_.-]{8,128}$")
_MAX_SESSIONS = 256
_MAX_MESSAGES = 20
_memory: OrderedDict[str, list[dict[str, str]]] = OrderedDict()


def validate_session_id(value: str | None) -> str | None:
    if value is None:
        return None
    return value if _SESSION_RE.fullmatch(value) else None


def _clean(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    cleaned = []
    for item in messages[-_MAX_MESSAGES:]:
        role = item.get("role")
        content = str(item.get("content", "")).strip()[:2000]
        if role in {"user", "assistant"} and content:
            cleaned.append({"role": role, "content": content})
    return cleaned


async def load_memory(session_id: str | None) -> list[dict[str, str]]:
    valid = validate_session_id(session_id)
    if not valid:
        return []
    try:
        stored = await load_agent_session(valid)
    except Exception:
        stored = None
    if stored is not None:
        return _clean(stored)
    return list(_memory.get(valid, []))


async def save_memory(session_id: str | None, messages: list[dict[str, str]]) -> None:
    valid = validate_session_id(session_id)
    if not valid:
        return
    cleaned = _clean(messages)
    try:
        if await save_agent_session(valid, cleaned):
            return
    except Exception:
        pass
    _memory[valid] = cleaned
    _memory.move_to_end(valid)
    while len(_memory) > _MAX_SESSIONS:
        _memory.popitem(last=False)


def clear_memory_for_tests() -> None:
    _memory.clear()
