from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.config import MAX_HISTORY_CHARS, MAX_HISTORY_ITEMS, MAX_MESSAGE_LENGTH


class HistoryItem(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=2000)


class AssistantRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=MAX_MESSAGE_LENGTH)
    history: list[HistoryItem] = Field(default_factory=list)

    @field_validator("message")
    @classmethod
    def sanitize_message(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("message cannot be empty or whitespace only")
        return stripped

    @field_validator("history")
    @classmethod
    def cap_history(cls, v: list) -> list:
        # Keep the most recent turns within a character budget so the full
        # request (system prompt + history + reply) stays under Groq's 8K
        # tokens-per-request limit.
        kept: list = []
        used = 0
        for item in reversed(v):
            used += len(item.content)
            if used > MAX_HISTORY_CHARS or len(kept) >= MAX_HISTORY_ITEMS:
                break
            kept.append(item)
        kept.reverse()
        return kept


class AssistantResponse(BaseModel):
    reply: str
