from dataclasses import dataclass

from app.ai.laya import RouteDecision, route_message
from app.ai.okf import retrieve_with_sources
from app.ai.presentation import direct_reply


@dataclass(frozen=True)
class PreparedTurn:
    decision: RouteDecision
    knowledge_context: str
    direct_reply: str | None = None
    sources: tuple[dict[str, str], ...] = ()


async def prepare_turn(message: str, history_items, language: str = "en") -> PreparedTurn:
    history = [
        {"role": item.role, "content": item.content}
        for item in history_items[-4:]
    ]
    decision = await route_message(message, history)
    if decision.scope == "prompt_attack":
        return PreparedTurn(
            decision,
            "",
            direct_reply("prompt_attack", language),
        )
    if decision.scope == "unrelated":
        return PreparedTurn(
            decision,
            "",
            direct_reply("unrelated", language),
        )
    query = " ".join([*(item.content for item in history_items[-2:]), message])
    result = retrieve_with_sources(query, decision.topic)
    return PreparedTurn(decision, result.context, sources=result.sources)
