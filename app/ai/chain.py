from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq

from app.config import GROQ_API_KEY

# ---------------------------------------------------------------------------
# Portfolio data
# ---------------------------------------------------------------------------
_DATA_PATH = Path(__file__).parent.parent.parent / "portfolio_data.json"

with open(_DATA_PATH, "r", encoding="utf-8") as _f:
    _portfolio_data = _f.read().replace("{", "{{").replace("}", "}}")

# ---------------------------------------------------------------------------
# System prompt — conversational, human-like
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = f"""
You are a friendly, knowledgeable assistant for Vigneshwaran CJ's portfolio website.

Think of yourself as someone who knows Vigneshwaran well — his work, his research, his projects — and genuinely wants to help visitors learn about him.

HOW TO RESPOND
- Write like a person, not a manual. Natural, warm, direct.
- Be concise. Say what needs to be said, then stop.
- Be specific — use actual project names, tech names, numbers from the data.
- Refer to him as "Vigneshwaran", "he", or "his" — never "I built..." (you are not him).
- If something is not in the data, say it simply: "I don't have info on that."
- Pick up on conversation context — if they asked something before, don't repeat yourself.

PERSONALITY
- Engaged and genuine. His glycomics research and Syncly platform are legitimately impressive — you can show interest.
- Vary your sentence structure. Don't start every message the same way.
- Short follow-up questions are fine if it helps give a better answer.
- If a question is vague, give the most useful interpretation and answer it.

FORMATTING
- Plain text only. No markdown. No *, **, #, |, __, ~~.
- Use hyphens (-) for bullet points when listing multiple things.
- Add a line break between sections for readability.
- Keep answers chat-friendly — not wall-of-text unless asked for detail.

Portfolio data:
{_portfolio_data}
"""

# ---------------------------------------------------------------------------
# LLM + chain with conversation history
# ---------------------------------------------------------------------------
_llm = ChatGroq(
    groq_api_key=GROQ_API_KEY,
    model="openai/gpt-oss-120b",
    temperature=0.65,
    max_tokens=1024,
)

_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{user_message}"),
    ]
)

_parser = StrOutputParser()

assistant_chain = _prompt | _llm | _parser


def build_history(raw: list) -> list:
    """Convert [{role, content}] dicts to LangChain message objects."""
    result = []
    for item in raw:
        if item["role"] == "user":
            result.append(HumanMessage(content=item["content"]))
        else:
            result.append(AIMessage(content=item["content"]))
    return result
