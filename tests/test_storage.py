import os
import unittest
from unittest.mock import AsyncMock, patch

os.environ.setdefault("GROQ_API_KEY", "test-only")

from app.services import storage


class StorageTests(unittest.IsolatedAsyncioTestCase):
    async def test_saved_session_round_trips_asyncpg_json_text(self):
        messages = [{"role": "user", "content": "Tell me about PocketPet"}]
        pool = AsyncMock()
        with patch.object(storage, "_pool", pool):
            self.assertTrue(await storage.save_agent_session("session-one", messages))
            # asyncpg returns JSON/JSONB as text unless a codec is configured.
            pool.fetchval.return_value = pool.execute.call_args.args[-1]
            self.assertEqual(await storage.load_agent_session("session-one"), messages)

    async def test_content_revision_round_trips_as_object(self):
        content = {"personal": {"name": "CJ"}, "projects": {}}
        pool = AsyncMock()
        with patch.object(storage, "_pool", pool):
            await storage.save_content_revision(content, "test revision")
            pool.fetchval.return_value = pool.fetchval.call_args.args[1]
            self.assertEqual(await storage.latest_content(), content)

    async def test_missing_session_returns_none(self):
        pool = AsyncMock()
        pool.fetchval.return_value = None
        with patch.object(storage, "_pool", pool):
            self.assertIsNone(await storage.load_agent_session("missing-session"))

    async def test_decoded_json_values_remain_supported(self):
        pool = AsyncMock()
        messages = [{"role": "assistant", "content": "Hello"}]
        with patch.object(storage, "_pool", pool):
            pool.fetchval.return_value = messages
            self.assertEqual(await storage.load_agent_session("session-one"), messages)
            pool.fetchval.return_value = {"personal": {"name": "CJ"}}
            self.assertEqual(await storage.latest_content(), {"personal": {"name": "CJ"}})
