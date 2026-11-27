import asyncio
import os
import unittest
from unittest import mock

os.environ.setdefault("GROQ_API_KEY", "test-key")

import app.services.storage as storage

SESSION_POOLER = "postgresql://postgres.abcdefghij:secret@aws-0-ap-south-1.pooler.supabase.com:5432/postgres"
TRANSACTION_POOLER = "postgresql://postgres.abcdefghij:secret@aws-0-ap-south-1.pooler.supabase.com:6543/postgres"


class ConnectionOptionsTests(unittest.TestCase):
    def test_session_pooler_keeps_statement_cache_and_requires_tls(self):
        dsn, options = storage.connection_options(SESSION_POOLER)
        self.assertEqual(dsn, SESSION_POOLER)
        self.assertEqual(options, {"ssl": "require"})

    def test_transaction_pooler_disables_prepared_statement_cache(self):
        _, options = storage.connection_options(TRANSACTION_POOLER)
        self.assertEqual(options["statement_cache_size"], 0)

    def test_pgbouncer_flag_is_removed_and_honoured(self):
        dsn, options = storage.connection_options(SESSION_POOLER + "?pgbouncer=true&application_name=portfolio")
        self.assertNotIn("pgbouncer", dsn)
        self.assertIn("application_name=portfolio", dsn)
        self.assertEqual(options["statement_cache_size"], 0)

    def test_explicit_sslmode_and_local_hosts_are_left_alone(self):
        self.assertNotIn("ssl", storage.connection_options(SESSION_POOLER + "?sslmode=verify-full")[1])
        self.assertEqual(storage.connection_options("postgresql://app:pw@localhost:5432/portfolio")[1], {})


class _FakeConnection:
    def __init__(self, statements):
        self.statements = statements

    async def execute(self, sql, *args):
        self.statements.append(sql)
        return "DELETE 0"


class _FakeAcquire:
    def __init__(self, connection):
        self.connection = connection

    async def __aenter__(self):
        return self.connection

    async def __aexit__(self, *exc):
        return False


class _FakePool:
    def __init__(self):
        self.statements = []

    def acquire(self):
        return _FakeAcquire(_FakeConnection(self.statements))

    async def execute(self, sql, *args):
        self.statements.append(sql)
        return "DELETE 0"

    async def close(self):
        pass


class ResilientStartupTests(unittest.TestCase):
    def setUp(self):
        storage._pool = None
        storage._last_attempt = 0.0

    def tearDown(self):
        storage._pool = None
        storage._last_attempt = 0.0

    def test_unreachable_database_does_not_stop_startup(self):
        async def refuse(*_args, **_kwargs):
            raise OSError("connection refused")

        with mock.patch.object(storage, "DATABASE_URL", SESSION_POOLER), \
                mock.patch.object(storage.asyncpg, "create_pool", refuse), \
                self.assertLogs("app.services.storage", level="WARNING") as logs:
            asyncio.run(storage.init_storage())
        self.assertIsNone(storage._pool)
        self.assertNotIn("secret", " ".join(logs.output))  # the URL/password is never logged
        with mock.patch.object(storage, "DATABASE_URL", SESSION_POOLER):
            self.assertEqual(storage.storage_status(), "unreachable")

    def test_reconnect_is_throttled(self):
        calls = 0

        async def refuse(*_args, **_kwargs):
            nonlocal calls
            calls += 1
            raise OSError("down")

        async def run():
            await storage.init_storage()
            await storage.ensure_storage()  # within the interval: no new attempt
            return await storage.ping()

        with mock.patch.object(storage, "DATABASE_URL", SESSION_POOLER), \
                mock.patch.object(storage.asyncpg, "create_pool", refuse), \
                self.assertLogs("app.services.storage", level="WARNING"):
            self.assertEqual(asyncio.run(run()), "unreachable")
        self.assertEqual(calls, 1)

    def test_schema_enables_row_level_security_on_every_table(self):
        pool = _FakePool()

        async def connect(*_args, **kwargs):
            self.assertEqual(kwargs.get("ssl"), "require")
            return pool

        with mock.patch.object(storage, "DATABASE_URL", SESSION_POOLER), \
                mock.patch.object(storage.asyncpg, "create_pool", connect):
            asyncio.run(storage.init_storage())
        rls = next(sql for sql in pool.statements if "ROW LEVEL SECURITY" in sql)
        for table in storage.TABLES:
            self.assertIn(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY", rls)
            self.assertTrue(any(f"CREATE TABLE IF NOT EXISTS {table}" in sql for sql in pool.statements), table)


if __name__ == "__main__":
    unittest.main()
