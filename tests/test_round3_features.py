import asyncio
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

os.environ.setdefault("GROQ_API_KEY", "test-key")

import httpx
from fastapi.testclient import TestClient

import app.limiter as limiter_module
import app.services.newsletter as newsletter
from app.ai.output_guard import guard_identifiers
from app.services import telemetry
from app.services.proof import summarize_activity
from app.services.resume_document import build_resume, render_text
from evals.answer_eval import forbidden_present, missing_fact_groups, parse_judgement, summarize, CaseResult
from main import app

FRONTEND_JOB = ("Frontend engineer: React, TypeScript, Next.js, Tailwind CSS, Redux, Vite. Build polished interfaces "
                "and design systems, with Jest and Playwright testing across browsers.")


class TailoredResumeTests(unittest.TestCase):
    def test_focus_terms_lead_skills_and_add_core_line(self):
        text = render_text(build_resume(["React", "TypeScript", "Tailwind CSS"]))
        self.assertIn("Core skills for this role: React, TypeScript, Tailwind CSS", text)
        skills = text.split("TECHNICAL SKILLS")[1]
        self.assertTrue(skills.strip("-\n ").startswith("Frontend Development"))

    def test_tailoring_never_invents_skills(self):
        base = render_text(build_resume())
        tailored = render_text(build_resume(["React"]))
        base_skills = base.split("TECHNICAL SKILLS")[1].split("WORK EXPERIENCE")[0]
        tailored_skills = tailored.split("TECHNICAL SKILLS")[1].split("WORK EXPERIENCE")[0]
        self.assertEqual(sorted(base_skills.replace(",", "\n").split()), sorted(tailored_skills.replace(",", "\n").split()))

    def test_untailored_resume_is_unchanged_by_feature(self):
        self.assertNotIn("Core skills for this role", render_text(build_resume()))

    def test_research_projects_are_not_duplicated_under_projects(self):
        text = render_text(build_resume(["RDKit", "Scikit-Learn", "Python"]))
        projects = text.split("PROJECTS")[1].split("EDUCATION")[0]
        self.assertNotIn("EGFR", projects)


class OutputGuardTests(unittest.TestCase):
    def test_removes_links_and_contacts_absent_from_sources(self):
        result = guard_identifiers("Email cj@fake-domain.com or visit https://evil.example.com/x or call +91 98765 43210.", "context")
        self.assertEqual(len(result.removed), 3)
        self.assertNotIn("fake-domain", result.text)
        self.assertNotIn("evil", result.text)
        self.assertTrue(result.text.endswith("the contact page."))

    def test_keeps_identifiers_found_in_context_or_published(self):
        context = "Live demo: https://glycanbench.sastra.edu/ and package on pypi.org/project/glycanbench"
        text = "Try https://glycanbench.sastra.edu/ or pypi.org/project/glycanbench, or email vigneshwarancj@gmail.com."
        result = guard_identifiers(text, context)
        self.assertEqual(result.removed, ())
        self.assertEqual(result.text, text)

    def test_ignores_versions_years_and_tech_names(self):
        text = "Built with Next.js and Socket.IO in 2025-2026, achieving AUC 0.983 on 1,344 glycans."
        self.assertEqual(guard_identifiers(text, "Socket.IO Next.js").removed, ())


class TelemetryTests(unittest.TestCase):
    def setUp(self):
        telemetry.reset_for_tests()

    def test_snapshot_reports_rates_and_percentiles_without_content(self):
        for value in (100, 200, 300, 400):
            telemetry.record_latency("assistant.generate", value)
        telemetry.record_llm_metric("assistant.answered", 3)
        telemetry.record_llm_metric("assistant.cache_hit")
        telemetry.record_text_volume("assistant", 400, 80)
        snap = telemetry.snapshot()
        self.assertEqual(snap["latency_ms"]["assistant.generate"]["count"], 4)
        self.assertEqual(snap["rates"]["cache_hit_rate"], 0.25)
        self.assertEqual(snap["estimated_tokens"]["assistant.input"], 100)


class ActivityTests(unittest.TestCase):
    def test_counts_recent_pushes_and_commits_only(self):
        now = datetime(2026, 11, 26, tzinfo=timezone.utc)
        events = [
            {"type": "PushEvent", "created_at": (now - timedelta(days=2)).isoformat(), "repo": {"name": "vigneshcj001/Pocketpet"}, "payload": {"distinct_size": 3}},
            {"type": "PushEvent", "created_at": (now - timedelta(days=40)).isoformat(), "repo": {"name": "vigneshcj001/old"}, "payload": {"distinct_size": 9}},
            {"type": "WatchEvent", "created_at": now.isoformat(), "repo": {"name": "x/y"}},
        ]
        summary = summarize_activity(events, now)
        self.assertEqual((summary["pushes"], summary["commits"]), (1, 3))
        self.assertEqual(summary["active_repos"][0]["name"], "Pocketpet")


class NewsletterTests(unittest.TestCase):
    def test_unsubscribe_tokens_are_per_address(self):
        with mock.patch.object(newsletter, "UNSUBSCRIBE_SECRET", "secret"):
            token = newsletter.unsubscribe_token("A@Example.com")
            self.assertTrue(newsletter.valid_unsubscribe("a@example.com", token))
            self.assertFalse(newsletter.valid_unsubscribe("b@example.com", token))

    def test_send_posts_one_email_per_recipient_with_unsubscribe_link(self):
        bodies = []

        def handler(request):
            bodies.append(request.read().decode())
            return httpx.Response(200, json={"id": "x"})

        settings = {"RESEND_API_KEY": "re_test", "NEWSLETTER_FROM": "CJ <n@example.com>", "UNSUBSCRIBE_SECRET": "s"}
        with mock.patch.multiple(newsletter, **settings):
            async def run():
                async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                    return await newsletter.send("New note", "Hello readers.\n\nSecond paragraph.", ["a@x.com", "b@x.com"], client)
            report = asyncio.run(run())
        self.assertEqual((report.sent, report.failed), (2, 0))
        self.assertIn("unsubscribe?email=a%40x.com", bodies[0])

    def test_send_refuses_without_configuration(self):
        with mock.patch.multiple(newsletter, RESEND_API_KEY="", NEWSLETTER_FROM="", UNSUBSCRIBE_SECRET=""):
            with self.assertRaises(newsletter.NewsletterNotConfigured):
                asyncio.run(newsletter.send("s", "text body", ["a@x.com"]))


class AnswerEvalScoringTests(unittest.TestCase):
    def test_fact_groups_accept_any_alternative(self):
        self.assertEqual(missing_fact_groups("Built with Tauri and Rust.", [["Tauri"], ["Rust", "Go"]]), [])
        self.assertEqual(missing_fact_groups("Built with Tauri.", [["Tauri"], ["Rust"]]), [["Rust"]])

    def test_forbidden_and_judgement_parsing(self):
        self.assertEqual(forbidden_present("Expected 12 LPA", ["LPA"]), ["LPA"])
        self.assertEqual(parse_judgement('```json\n{"faithful": false, "unsupported_claims": ["x"]}\n```'), (False, ["x"]))
        self.assertEqual(parse_judgement("nonsense"), (None, []))

    def test_summary_applies_thresholds(self):
        results = [CaseResult("a", "q", answer="ok"), CaseResult("b", "q", refused=True, expect_refusal=True),
                   CaseResult("c", "q", missing_facts=[["x"]])]
        metrics = summarize(results, {"fact_pass_rate": 0.85, "refusal_accuracy": 1.0})
        self.assertEqual(metrics["fact_pass_rate"], 0.5)
        self.assertEqual(metrics["failed_thresholds"], ["fact_pass_rate"])


class CommunityApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.client.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)

    def setUp(self):
        limiter_module.limiter.reset()

    def test_tailored_resume_endpoint(self):
        response = self.client.post("/api/resume/tailored", json={"job_description": FRONTEND_JOB, "format": "txt"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("Core skills for this role", response.text)
        self.assertGreater(int(response.headers["x-matched-terms"]), 3)
        pdf = self.client.post("/api/resume/tailored", json={"job_description": FRONTEND_JOB})
        self.assertTrue(pdf.content.startswith(b"%PDF"))
        self.assertIn("tailored.pdf", pdf.headers["content-disposition"])

    def test_share_requires_result_shape_and_database(self):
        bad = self.client.post("/api/match/share", json={"keywords": {}, "generated_by": "anything"})
        self.assertEqual(bad.status_code, 422)
        good = {"keywords": {"matched": [], "missing": [], "coverage": None}, "generated_by": "keywords"}
        self.assertEqual(self.client.post("/api/match/share", json=good).status_code, 503)
        self.assertEqual(self.client.get("/api/match/share/bad").status_code, 404)

    def test_testimonial_requires_consent_and_hides_without_database(self):
        payload = {"name": "Ada", "role": "Lead", "relationship": "Manager", "quote": "A thoughtful engineer who ships carefully tested work.", "consent": False}
        self.assertEqual(self.client.post("/api/testimonials", json=payload).status_code, 422)
        self.assertEqual(self.client.get("/api/testimonials").json(), {"testimonials": []})

    def test_client_error_report_accepted_and_admin_protected(self):
        response = self.client.post("/api/client-errors", json={"message": "TypeError: x", "path": "/match?draft=secret"})
        self.assertEqual(response.status_code, 202)
        self.assertEqual(self.client.get("/api/admin/metrics").status_code, 401)
        self.assertEqual(self.client.get("/api/admin/client-errors").status_code, 401)

    def test_invalid_unsubscribe_link_is_rejected(self):
        response = self.client.get("/api/newsletter/unsubscribe", params={"email": "a@x.com", "token": "nope"})
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
