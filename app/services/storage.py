import json
from typing import Any

from app.config import DATABASE_URL

try:
    import asyncpg
except ImportError:  # Local static validation can run before dependencies install.
    asyncpg = None

_pool = None


class StorageUnavailable(RuntimeError):
    pass


async def init_storage() -> None:
    global _pool
    if not DATABASE_URL or asyncpg is None:
        return
    _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=3, command_timeout=10)
    async with _pool.acquire() as connection:
        await connection.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_content_revisions (
              id BIGSERIAL PRIMARY KEY, content JSONB NOT NULL, note TEXT NOT NULL,
              created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS portfolio_events (
              id BIGSERIAL PRIMARY KEY, name TEXT NOT NULL, path TEXT NOT NULL,
              properties JSONB NOT NULL DEFAULT '{}'::jsonb, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS portfolio_contacts (
              id BIGSERIAL PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL,
              message TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS portfolio_subscribers (
              email TEXT PRIMARY KEY, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """)


async def close_storage() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


def connected() -> bool:
    return _pool is not None


def _require_pool():
    if _pool is None:
        raise StorageUnavailable("Database storage is not configured")
    return _pool


async def record_event(name: str, path: str, properties: dict[str, Any]) -> None:
    if _pool:
        await _pool.execute(
            "INSERT INTO portfolio_events(name,path,properties) VALUES($1,$2,$3::jsonb)",
            name, path, json.dumps(properties),
        )


async def save_contact(name: str, email: str, message: str) -> None:
    await _require_pool().execute(
        "INSERT INTO portfolio_contacts(name,email,message) VALUES($1,$2,$3)",
        name, email.lower(), message,
    )


async def save_subscriber(email: str) -> None:
    await _require_pool().execute(
        "INSERT INTO portfolio_subscribers(email) VALUES($1) ON CONFLICT(email) DO NOTHING",
        email.lower(),
    )


async def latest_content():
    if not _pool:
        return None
    return await _pool.fetchval(
        "SELECT content FROM portfolio_content_revisions ORDER BY id DESC LIMIT 1"
    )


async def save_content_revision(content: dict[str, Any], note: str) -> int:
    return await _require_pool().fetchval(
        "INSERT INTO portfolio_content_revisions(content,note) VALUES($1::jsonb,$2) RETURNING id",
        json.dumps(content), note,
    )


async def analytics_summary() -> list[dict[str, Any]]:
    rows = await _require_pool().fetch(
        "SELECT name, COUNT(*) AS count, MAX(created_at) AS last_seen "
        "FROM portfolio_events GROUP BY name ORDER BY count DESC"
    )
    return [dict(row) for row in rows]
