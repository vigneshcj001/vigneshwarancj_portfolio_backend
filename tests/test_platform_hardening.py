import asyncio
import os
import unittest
from unittest import mock

os.environ.setdefault("GROQ_API_KEY", "test-key")

from fastapi.testclient import TestClient
from starlette.requests import Request

import app.limiter as limiter_module
import app.services.proof as proof
from main import app


def _request(peer: str, forwarded: str | None = None) -> Request:
    headers = [(b"x-forwarded-for", forwarded.encode())] if forwarded else []
    return Request({"type": "http", "headers": headers, "client": (peer, 1234), "method": "GET", "path": "/"})


class ClientIpTests(unittest.TestCase):
    def test_uses_socket_peer_when_no_proxy_is_trusted(self):
        with mock.patch.object(limiter_module, "TRUSTED_PROXY_COUNT", 0):
            self.assertEqual(limiter_module.client_ip(_request("10.0.0.1", "203.0.113.9")), "10.0.0.1")

    def test_uses_proxy_appended_address_and_ignores_spoofed_entries(self):
        with mock.patch.object(limiter_module, "TRUSTED_PROXY_COUNT", 1):
            ip = limiter_module.client_ip(_request("10.0.0.1", "1.1.1.1, 203.0.113.9"))
        self.assertEqual(ip, "203.0.113.9")

    def test_falls_back_when_header_is_shorter_than_proxy_chain(self):
        with mock.patch.object(limiter_module, "TRUSTED_PROXY_COUNT", 2):
            self.assertEqual(limiter_module.client_ip(_request("10.0.0.1", "203.0.113.9")), "10.0.0.1")


class ApiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.client.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)

    def test_health_reports_storage_and_request_id(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["database"], "not_configured")
        self.assertIn("uptime_seconds", body)
        self.assertTrue(response.headers.get("x-request-id"))

    def test_rate_limit_uses_detail_shape_with_retry_after(self):
        limiter_module.limiter.reset()
        try:
            statuses = [
                self.client.post("/api/demo/aiora", json={"input": "book"}).status_code
                for _ in range(11)
            ]
            self.assertEqual(statuses[-1], 429)
            response = self.client.post("/api/demo/aiora", json={"input": "book"})
            self.assertEqual(response.status_code, 429)
            self.assertIn("Too many requests", response.json()["detail"])
            self.assertGreater(int(response.headers["retry-after"]), 0)
        finally:
            limiter_module.limiter.reset()

    def test_og_card_rejects_unexpected_slugs(self):
        self.assertEqual(self.client.get("/api/og/aiora.svg").status_code, 200)
        self.assertEqual(self.client.get("/api/og/%3Cscript%3E.svg").status_code, 404)


class ProofCacheTests(unittest.TestCase):
    def setUp(self):
        proof._cache.update(expires=0.0, value=None, retry_after=0.0)

    def tearDown(self):
        proof._cache.update(expires=0.0, value=None, retry_after=0.0)

    def test_concurrent_misses_share_one_refresh(self):
        calls = 0

        async def fake_refresh():
            nonlocal calls
            calls += 1
            await asyncio.sleep(0.01)
            return {"github": [], "pypi": None, "cached_at": "now"}

        async def run():
            with mock.patch.object(proof, "_refresh", fake_refresh):
                return await asyncio.gather(*(proof.public_metadata() for _ in range(5)))

        results = asyncio.run(run())
        self.assertEqual(calls, 1)
        self.assertTrue(all(result["cached_at"] == "now" for result in results))

    def test_failure_backs_off_instead_of_retrying_every_request(self):
        calls = 0

        async def failing_refresh():
            nonlocal calls
            calls += 1
            raise TimeoutError()

        async def run():
            with mock.patch.object(proof, "_refresh", failing_refresh):
                for _ in range(3):
                    with self.assertRaises(proof.MetadataUnavailable):
                        await proof.public_metadata()

        asyncio.run(run())
        self.assertEqual(calls, 1)


if __name__ == "__main__":
    unittest.main()
