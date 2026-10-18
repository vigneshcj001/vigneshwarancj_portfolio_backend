import re
from dataclasses import dataclass
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agent.protocol import ToolTrace, UiAction
from app.agent.tools import PROJECT_TARGETS, ToolInvocation, execute_tool, project_slug
from app.ai.laya import RouteDecision, route_message
from app.ai.presentation import FOLLOWUPS, direct_reply

MAX_TOOL_CALLS = 4
_NAVIGATE_RE = re.compile(r"\b(show|open|take me|go to|navigate|view|visit)\b", re.IGNORECASE)
_HIGHLIGHT_RE = re.compile(r"\b(highlight|point out|where is)\b", re.IGNORECASE)
_WALKTHROUGH_RE = re.compile(r"\b(walkthrough|tour|step[- ]by[- ]step)\b", re.IGNORECASE)


class AgentState(TypedDict, total=False):
    message: str
    history: list[dict[str, str]]
    language: str
    decision: dict[str, str]
    direct_reply: str | None
    tool_calls: list[dict[str, Any]]
    contexts: list[str]
    sources: list[dict[str, str]]
    actions: list[dict[str, Any]]
    tool_trace: list[dict[str, str]]
    project: str | None


@dataclass(frozen=True)
class AgentTurn:
    decision: RouteDecision
    knowledge_context: str
    direct_reply: str | None
    sources: tuple[dict[str, str], ...]
    actions: tuple[UiAction, ...]
    tool_trace: tuple[ToolTrace, ...]
    followups: tuple[str, ...]
    project: str | None


def _topic_target(topic: str, slug: str | None) -> str:
    if slug:
        return PROJECT_TARGETS[slug]
    return {
        "projects": "projects.list", "skills": "skills.grid",
        "experience": "experience.timeline", "research": "publications.list",
        "education": "about.profile", "profile": "about.profile",
        "contact": "contact.form",
    }.get(topic, "home.hero")


def build_tool_plan(message: str, topic: str) -> list[ToolInvocation]:
    lower = message.casefold()
    slug = project_slug(message)
    calls: list[ToolInvocation] = []
    if slug:
        calls.append(ToolInvocation("search_portfolio", {"query": message, "topic": "projects", "limit": 3}))
        calls.append(ToolInvocation("get_project_details", {"project": slug}))
    elif topic == "skills":
        calls.append(ToolInvocation("get_skills", {}))
    elif topic == "experience":
        calls.append(ToolInvocation("get_experience", {"query": message}))
    elif "resume" in lower or "résumé" in lower or "cv" in lower:
        calls.append(ToolInvocation("get_resume", {"section": "summary"}))
    else:
        calls.append(ToolInvocation("search_portfolio", {"query": message, "topic": topic if topic in {"profile", "projects", "skills", "experience", "research", "education", "contact"} else "general"}))

    target = _topic_target(topic, slug)
    if _WALKTHROUGH_RE.search(message) and slug:
        calls.append(ToolInvocation("start_project_walkthrough", {"project": slug}))
    if _NAVIGATE_RE.search(message):
        calls.append(ToolInvocation("navigate_to_section", {"target": target}))
    elif _HIGHLIGHT_RE.search(message):
        calls.append(ToolInvocation("highlight_element", {"target": target}))
    if topic == "contact" or re.search(r"\b(contact|hire|reach|email)\b", lower):
        calls.append(ToolInvocation("prepare_contact_action", {"topic": message}))
    return calls[:MAX_TOOL_CALLS]


def route_node(state: AgentState) -> AgentState:
    decision_data = state["decision"]
    decision = RouteDecision(decision_data["scope"], decision_data["topic"], decision_data["source"])
    direct = direct_reply(decision.scope, state["language"]) if decision.scope in {"prompt_attack", "unrelated"} else None
    return {"decision": {"scope": decision.scope, "topic": decision.topic, "source": decision.source}, "direct_reply": direct}


def plan_node(state: AgentState) -> AgentState:
    if state.get("direct_reply"):
        return {"tool_calls": []}
    topic = state["decision"]["topic"]
    calls = build_tool_plan(state["message"], topic)
    return {"tool_calls": [{"name": call.name, "arguments": call.arguments} for call in calls]}


def execute_node(state: AgentState) -> AgentState:
    contexts: list[str] = []
    sources: list[dict[str, str]] = []
    actions: list[dict[str, Any]] = []
    trace: list[dict[str, str]] = []
    for raw in state.get("tool_calls", [])[:MAX_TOOL_CALLS]:
        invocation = ToolInvocation(raw["name"], raw.get("arguments", {}))
        try:
            outcome = execute_tool(invocation)
            if outcome.context:
                contexts.append(outcome.context)
            sources.extend(outcome.sources)
            actions.extend(action.model_dump() for action in outcome.actions)
            trace.append(ToolTrace(name=invocation.name, summary=outcome.summary).model_dump())
        except Exception:
            trace.append(ToolTrace(name=invocation.name, status="failed", summary="Tool input rejected or unavailable").model_dump())
    deduped_sources = list({source["url"]: {key: value for key, value in source.items() if key != "path"} for source in sources}.values())[:4]
    deduped_actions = list({f"{item['type']}:{item['target']}": item for item in actions}.values())
    project = project_slug(state["message"])
    return {
        "contexts": contexts, "sources": deduped_sources, "actions": deduped_actions,
        "tool_trace": trace, "project": project,
    }


_builder = StateGraph(AgentState)
_builder.add_node("route", route_node)
_builder.add_node("plan", plan_node)
_builder.add_node("execute", execute_node)
_builder.add_edge(START, "route")
_builder.add_edge("route", "plan")
_builder.add_edge("plan", "execute")
_builder.add_edge("execute", END)
portfolio_agent_graph = _builder.compile()


async def run_agent_turn(message: str, history: list[dict[str, str]], language: str, session_id: str | None = None) -> AgentTurn:
    routed = await route_message(message, history[-4:])
    result = portfolio_agent_graph.invoke(
        {
            "message": message, "history": history, "language": language,
            "decision": {"scope": routed.scope, "topic": routed.topic, "source": routed.source},
        },
        config={"run_name": "portfolio-agent-turn", "tags": ["portfolio", "agentic"], "metadata": {"session_id": session_id or "ephemeral"}},
    )
    decision_data = result["decision"]
    decision = RouteDecision(decision_data["scope"], decision_data["topic"], decision_data["source"])
    return AgentTurn(
        decision=decision,
        knowledge_context="\n\n---\n\n".join(result.get("contexts", [])),
        direct_reply=result.get("direct_reply"),
        sources=tuple(result.get("sources", [])),
        actions=tuple(UiAction.model_validate(action) for action in result.get("actions", [])),
        tool_trace=tuple(ToolTrace.model_validate(item) for item in result.get("tool_trace", [])),
        followups=tuple(FOLLOWUPS.get(decision.topic, FOLLOWUPS["general"])),
        project=result.get("project"),
    )
