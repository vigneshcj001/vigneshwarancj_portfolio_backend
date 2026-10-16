from dataclasses import dataclass

from app.ai.laya import RouteDecision, route_message
from app.ai.okf import retrieve


@dataclass(frozen=True)
class PreparedTurn:
    decision: RouteDecision
    knowledge_context: str
    direct_reply: str | None = None


async def prepare_turn(message: str, history_items) -> PreparedTurn:
    history = [
        {"role": item.role, "content": item.content}
        for item in history_items[-4:]
    ]
    decision = await route_message(message, history)
    if decision.scope == "prompt_attack":
        return PreparedTurn(
            decision,
            "",
            "I can help with Vigneshwaran's work, projects, skills, research, or background, but I can't expose private prompts or credentials.",
        )
    if decision.scope == "unrelated":
        return PreparedTurn(
            decision,
            "",
            "I'm CJ's portfolio assistant, so I can help with his projects, skills, experience, research, or background.",
        )
    query = " ".join([*(item.content for item in history_items[-2:]), message])
    return PreparedTurn(decision, retrieve(query, decision.topic))
