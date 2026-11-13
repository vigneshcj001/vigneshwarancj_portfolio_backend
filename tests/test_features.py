import asyncio
import io
import os
import unittest
import zipfile
from unittest import mock
from xml.dom import minidom

os.environ.setdefault("GROQ_API_KEY", "test-key")

from fastapi.testclient import TestClient

import app.limiter as limiter_module
import app.routes.assistant as assistant_routes
import app.services.match as match
from app.agent.memory import clear_memory_for_tests, delete_memory, load_memory, save_memory
from app.models import AssistantRequest
from app.routes.resume import render_docx, render_pdf
from app.services.resume_document import build_resume, clip, render_text
from main import app

JOB = (
    "We are hiring an AI Engineer to build LLM-powered products. You will design pipelines with LangChain, "
    "ship FastAPI and Node.js services, use PostgreSQL and Redis, and deploy with Docker on AWS. "
    "Experience with Kafka and Terraform is a plus. Strong R&D mindset; go the extra mile."
)


class JobMatchTests(unittest.TestCase):
    def test_keyword_analysis_splits_evidence_and_gaps(self):
        result = match.keyword_analysis(JOB)
        matched = {item["term"] for item in result["matched"]}
        self.assertTrue({"FastAPI", "Node.js", "PostgreSQL", "Redis", "Docker", "AWS", "LangChain"} <= matched)
        self.assertIn("Kafka", result["missing"])
        self.assertIn("Terraform", result["missing"])
        self.assertTrue(all(item["evidence"] for item in result["matched"]))
        self.assertGreater(result["coverage"], 0.5)

    def test_prose_does_not_create_false_language_matches(self):
        result = match.keyword_analysis(JOB)
        terms = {item["term"] for item in result["matched"]} | set(result["missing"])
        self.assertNotIn("R", terms)  # "R&D"
        self.assertNotIn("Go", terms)  # "go the extra mile"

    def test_assessment_parser_validates_shape(self):
        raw = '```json\n{"summary": "Good fit.", "requirements": [' \
              '{"requirement": "FastAPI", "status": "strong", "evidence": "Bullion Handler"},' \
              '{"requirement": "Kafka", "status": "unknown", "evidence": "x"}]}\n```'
        parsed = match._parse_assessment(raw)
        self.assertEqual(parsed["summary"], "Good fit.")
        self.assertEqual([item["requirement"] for item in parsed["requirements"]], ["FastAPI"])
        self.assertIsNone(match._parse_assessment("not json"))
        self.assertIsNone(match._parse_assessment('{"summary": "x", "requirements": []}'))

    def test_falls_back_to_keywords_when_model_fails(self):
        async def failing(*_):
            return None, []

        with mock.patch.object(match, "ai_assessment", failing):
            result = asyncio.run(match.analyze_job(JOB))
        self.assertEqual(result["generated_by"], "keywords")
        self.assertEqual(result["requirements"], [])
        self.assertTrue(result["keywords"]["matched"])


class ApiFeatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.client.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)

    def setUp(self):
        limiter_module.limiter.reset()

    def test_match_endpoint_validates_and_returns_analysis(self):
        self.assertEqual(self.client.post("/api/match", json={"job_description": "too short"}).status_code, 422)
        response = self.client.post("/api/match", json={"job_description": JOB, "use_ai": False})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["generated_by"], "keywords")

    def test_session_delete_endpoint(self):
        self.assertEqual(self.client.delete("/api/assistant/session/visitor-session-123").status_code, 204)
        self.assertEqual(self.client.delete("/api/assistant/session/bad!").status_code, 400)

    def test_resume_downloads_in_three_formats(self):
        pdf = self.client.get("/api/resume")
        self.assertEqual(pdf.status_code, 200)
        self.assertTrue(pdf.content.startswith(b"%PDF"))
        docx = self.client.get("/api/resume.docx")
        self.assertEqual(docx.status_code, 200)
        self.assertIn("Resume.docx", docx.headers["content-disposition"])
        text = self.client.get("/api/resume.txt")
        self.assertIn("WORK EXPERIENCE", text.text)

    def test_funnel_requires_admin_key(self):
        self.assertEqual(self.client.get("/api/admin/funnel").status_code, 401)


class SessionMemoryTests(unittest.TestCase):
    def setUp(self):
        clear_memory_for_tests()

    def test_delete_erases_process_memory(self):
        session = "visitor-session-456"
        asyncio.run(save_memory(session, [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]))
        self.assertEqual(len(asyncio.run(load_memory(session))), 2)
        self.assertTrue(asyncio.run(delete_memory(session)))
        self.assertEqual(asyncio.run(load_memory(session)), [])
        self.assertFalse(asyncio.run(delete_memory("bad id!")))


class AnswerCacheTests(unittest.TestCase):
    def setUp(self):
        assistant_routes._response_cache.clear()

    def tearDown(self):
        assistant_routes._response_cache.clear()

    def _payload(self, message):
        return AssistantRequest(message=message, language="en", session_id="visitor-session-789")

    def test_opening_questions_share_a_key_despite_session_and_formatting(self):
        first = assistant_routes._cache_key(self._payload("What is PocketPet?"), [])
        second = assistant_routes._cache_key(self._payload("  what is   pocketpet "), [])
        self.assertIsNotNone(first)
        self.assertEqual(first, second)

    def test_follow_ups_are_not_cached(self):
        history = [{"role": "user", "content": "Tell me about AIORA"}]
        self.assertIsNone(assistant_routes._cache_key(self._payload("And the queues?"), history))

    def test_cached_answers_do_not_keep_a_visitor_session_id(self):
        key = assistant_routes._cache_key(self._payload("What is PocketPet?"), [])
        asyncio.run(assistant_routes._remember(key, {"reply": "A desktop companion.", "session_id": "visitor-session-789"}))
        cached = asyncio.run(assistant_routes._cached(key))
        self.assertEqual(cached["reply"], "A desktop companion.")
        self.assertIsNone(cached["session_id"])


class ResumeDocumentTests(unittest.TestCase):
    def test_clip_never_trails_off_mid_sentence(self):
        text = "Service that reads invoices with vision models, then runs a two-stage rules engine, and emails reports. " * 3
        clipped = clip(text, 120)
        self.assertLessEqual(len(clipped), 121)
        self.assertTrue(clipped.endswith("."))
        self.assertNotIn("…", clipped)

    def test_resume_uses_standard_ats_sections_with_contact_in_body(self):
        doc = build_resume()
        headings = [block.text for block in doc.blocks if block.kind == "heading"]
        for expected in ("Professional Summary", "Technical Skills", "Work Experience", "Projects", "Education"):
            self.assertIn(expected, headings)
        contact = next(block.text for block in doc.blocks if block.kind == "contact")
        self.assertIn("@", contact)
        self.assertIn("India", contact)
        self.assertTrue(doc.keywords)

    def test_renderers_produce_valid_files(self):
        doc = build_resume()
        self.assertTrue(render_pdf(doc).startswith(b"%PDF"))
        package = zipfile.ZipFile(io.BytesIO(render_docx(doc)))
        for part in ("[Content_Types].xml", "word/document.xml", "word/styles.xml", "docProps/core.xml"):
            minidom.parseString(package.read(part))
        document = package.read("word/document.xml").decode()
        self.assertIn("<w:tab/>", document)
        self.assertNotIn("\t", document)  # literal tabs are not tabs in OOXML
        text = render_text(doc)
        self.assertIn("PROFESSIONAL SUMMARY", text)
        self.assertNotIn("…", text)


if __name__ == "__main__":
    unittest.main()
