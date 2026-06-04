from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.config import MAX_MESSAGE_LENGTH


class HistoryItem(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=2000)


class AssistantRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=MAX_MESSAGE_LENGTH)
    history: list[HistoryItem] = Field(default_factory=list)

    @field_validator("message")
    @classmethod
    def sanitize_message(cls, v: str) -> str:
        return v.strip()

    @field_validator("history")
    @classmethod
    def cap_history(cls, v: list) -> list:
        return v[-20:]  # keep last 20 messages (10 user-assistant pairs)


class AssistantResponse(BaseModel):
    reply: str
