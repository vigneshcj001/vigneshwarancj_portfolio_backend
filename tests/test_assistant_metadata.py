import unittest

from pydantic import ValidationError

from app.ai.laya import RouteDecision
from app.ai.okf import retrieve_with_sources
from app.ai.orchestrator import PreparedTurn
from app.ai.presentation import LANGUAGE_NAMES, direct_reply, response_metadata
from app.models import AssistantRequest


class AssistantMetadataTests(unittest.TestCase):
    def test_selected_language_is_validated(self):
        request = AssistantRequest(message="Tell me about AIORA", language="ta")
        self.assertEqual("Tamil", LANGUAGE_NAMES[request.language])
        with self.assertRaises(ValidationError):
            AssistantRequest(message="Hello", language="de")
        self.assertIn("திட்டங்கள்", direct_reply("unrelated", "ta"))

    def test_retrieval_returns_public_source_links(self):
        result = retrieve_with_sources("PocketPet approval gates", "projects")
        self.assertIn("approval gates", result.context)
        self.assertEqual("/projects/pocketpet", result.sources[0]["url"])
        glycanbench = retrieve_with_sources("GlycanBench MPNN tools", "projects")
        self.assertEqual("/projects/glycanbench", glycanbench.sources[0]["url"])

    def test_response_metadata_includes_project_and_followups(self):
        prepared = PreparedTurn(
            RouteDecision("portfolio", "projects", "local"),
            "context",
            sources=({"title": "AIORA", "kind": "Project", "path": "projects/aiora.md", "url": "/projects/aiora"},),
        )
        metadata = response_metadata(prepared)
        self.assertEqual("aiora", metadata["project"])
        self.assertEqual(3, len(metadata["followups"]))
        self.assertNotIn("path", metadata["sources"][0])


if __name__ == "__main__":
    unittest.main()
