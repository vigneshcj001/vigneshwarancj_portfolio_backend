import os
import unittest
from unittest.mock import AsyncMock, patch

os.environ.setdefault("GROQ_API_KEY", "test-only")
os.environ["LANGCHAIN_TRACING_V2"] = "false"

from app.config import MAX_HISTORY_CHARS, MAX_HISTORY_ITEMS
from app.models import AssistantRequest
from app.routes.assistant import _history


class AssistantHistoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_restored_history_obeys_request_budget(self):
        stored = [
            {"role": "user" if index % 2 == 0 else "assistant", "content": str(index) * 100}
            for index in range(20)
        ]
        payload = AssistantRequest(message="What about its safety?", session_id="session-one")
        with patch("app.routes.assistant.load_memory", AsyncMock(return_value=stored)):
            items, raw = await _history(payload)
        self.assertLessEqual(len(items), MAX_HISTORY_ITEMS)
        self.assertLessEqual(sum(len(item.content) for item in items), MAX_HISTORY_CHARS)
        self.assertEqual(raw[-1], stored[-1])
        self.assertEqual(raw, [item.model_dump() for item in items])

    async def test_client_history_is_used_without_saved_session(self):
        payload = AssistantRequest(message="More?", history=[{"role": "user", "content": "PocketPet"}])
        with patch("app.routes.assistant.load_memory", AsyncMock(return_value=[])):
            items, raw = await _history(payload)
        self.assertEqual(raw, [{"role": "user", "content": "PocketPet"}])
        self.assertEqual(items[0].content, "PocketPet")
