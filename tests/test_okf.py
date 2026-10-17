import unittest

from app.ai.okf import load_bundle, retrieve
from app.content import load_portfolio


class OkfKnowledgeTests(unittest.TestCase):
    def test_bundle_loads_every_indexed_document(self):
        entries = load_bundle()
        self.assertEqual(25, len(entries))
        self.assertEqual(len(entries), len({entry.path for entry in entries}))

    def test_project_retrieval_selects_named_project(self):
        context = retrieve("How does PocketPet protect sensitive actions?", "projects")
        self.assertIn("SOURCE: projects/pocketpet.md", context)
        self.assertIn("approval gates", context)

    def test_research_retrieval_contains_glycanbench_evidence(self):
        context = retrieve("GlycanBench dataset validation and MPNN", "research")
        self.assertIn("1,344", context)
        self.assertIn("GlycanBench", context)

    def test_markdown_compiles_into_portfolio_schema(self):
        portfolio = load_portfolio()
        self.assertEqual(10, len(portfolio["projects"]))
        self.assertEqual(4, len(portfolio["work_experience"]))
        self.assertEqual("Vigneshwaran C. J.", portfolio["personal"]["name"])
        self.assertIn("PocketPet", portfolio["projects"])


if __name__ == "__main__":
    unittest.main()
