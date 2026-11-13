import os
import unittest

os.environ.setdefault("GROQ_API_KEY", "test-key")

from app.ai.okf import _query_tokens
from evals.retrieval_eval import run


class RetrievalQualityTests(unittest.TestCase):
    """Regression gate on retrieval quality (see evals/retrieval_cases.json).

    Thresholds sit just under the measured baseline (recall@4 0.958, direct 1.0,
    MRR 0.833 on 12 Nov 2026) so a change that makes the assistant miss the
    documents it needs fails CI instead of silently degrading answers.
    """

    @classmethod
    def setUpClass(cls):
        cls.results, cls.metrics = run()

    def test_every_direct_question_retrieves_its_document(self):
        misses = [item.id for item in self.results if item.style == "direct" and not item.hit]
        self.assertEqual(misses, [])

    def test_overall_recall_and_ranking_hold_baseline(self):
        self.assertGreaterEqual(self.metrics["recall@4"], 0.9)
        self.assertGreaterEqual(self.metrics["mrr"], 0.75)

    def test_query_expansion_bridges_everyday_phrasing(self):
        self.assertIn("present", _query_tokens("Where is he working now?"))
        self.assertNotIn("role", _query_tokens("Any work on glycans?"))


if __name__ == "__main__":
    unittest.main()
