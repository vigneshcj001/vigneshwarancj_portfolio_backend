import unittest

from app.ai.okf import load_bundle, retrieve


class OkfKnowledgeTests(unittest.TestCase):
    def test_bundle_loads_every_indexed_document(self):
        entries = load_bundle()
        self.assertEqual(15, len(entries))
        self.assertEqual(len(entries), len({entry.path for entry in entries}))

    def test_project_retrieval_selects_named_project(self):
        context = retrieve("How does PocketPet protect sensitive actions?", "projects")
        self.assertIn("SOURCE: projects/pocketpet.md", context)
        self.assertIn("approval gates", context)

    def test_research_retrieval_contains_glycanbench_evidence(self):
        context = retrieve("GlycanBench dataset validation and MPNN", "research")
        self.assertIn("1,344", context)
        self.assertIn("GlycanBench", context)


if __name__ == "__main__":
    unittest.main()
