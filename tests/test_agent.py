import os
import asyncio
import unittest

from pydantic import ValidationError

os.environ.setdefault("GROQ_API_KEY", "test-key")
os.environ["LANGCHAIN_API_KEY"] = ""
os.environ["LANGCHAIN_TRACING_V2"] = "false"

from app.agent.graph import build_tool_plan, portfolio_agent_graph
from app.agent.memory import clear_memory_for_tests, load_memory, save_memory
from app.agent.protocol import UiAction
from app.agent.tools import SearchPortfolioInput, search_portfolio


class AgentToolTests(unittest.TestCase):
    def setUp(self):
        clear_memory_for_tests()

    def test_project_plan_uses_search_details_and_safe_navigation(self):
        plan = build_tool_plan("Show me the PocketPet project", "projects")
        self.assertEqual(["search_portfolio", "get_project_details", "navigate_to_section"], [item.name for item in plan])
        self.assertLessEqual(len(plan), 4)

    def test_action_target_is_allowlisted(self):
        with self.assertRaises(ValidationError):
            UiAction(type="navigate", target="javascript:alert(1)", label="Unsafe")

    def test_search_reads_verified_markdown(self):
        outcome = search_portfolio(SearchPortfolioInput(query="PocketPet approval gates", topic="projects"))
        self.assertIn("approval gates", outcome.context)
        self.assertTrue(any(source["url"] == "/projects/pocketpet" for source in outcome.sources))

    def test_aa_session_memory_is_isolated(self):
        async def scenario():
            await save_memory("session-one", [{"role": "user", "content": "PocketPet"}])
            await save_memory("session-two", [{"role": "user", "content": "GlycanBench"}])
            self.assertEqual("PocketPet", (await load_memory("session-one"))[0]["content"])
            self.assertEqual("GlycanBench", (await load_memory("session-two"))[0]["content"])
        asyncio.run(scenario())

    def test_langgraph_vertical_slice_returns_action_and_grounding(self):
        turn = portfolio_agent_graph.invoke({
            "message": "Show me PocketPet", "history": [], "language": "en",
            "decision": {"scope": "portfolio", "topic": "projects", "source": "test"},
        })
        self.assertIn("approval gates", "\n".join(turn["contexts"]))
        self.assertIn("search_portfolio", [item["name"] for item in turn["tool_trace"]])
        self.assertTrue(any(action["type"] == "navigate" and action["target"] == "projects.pocketpet" for action in turn["actions"]))


if __name__ == "__main__":
    unittest.main()
