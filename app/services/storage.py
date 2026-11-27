import asyncio
import json
import logging
import time
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.config import ANSWER_CACHE_DAYS, DATABASE_URL, SESSION_RETENTION_DAYS

SHARE_RETENTION_DAYS = 30
CONNECT_TIMEOUT_SECONDS = 10
RECONNECT_INTERVAL_SECONDS = 60
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "postgres", "db", "host.docker.internal"}
# Every table the app creates. Row Level Security is enabled on all of them so
# hosted Postgres with a public data API (Supabase PostgREST) exposes nothing;
# the app connects as the table owner, which RLS does not restrict.
TABLES = (
    "portfolio_content_revisions", "portfolio_events", "portfolio_contacts", "portfolio_subscribers",
    "portfolio_agent_sessions", "portfolio_answer_cache", "portfolio_match_shares", "portfolio_testimonials",
)

try:
    import asyncpg
except ImportError:  # Local static validation can run before dependencies install.
    asyncpg = None

logger = logging.getLogger(__name__)
_pool = None
_last_attempt = 0.0
_last_error = ""


class StorageUnavailable(RuntimeError):
    pass


def connection_options(dsn: str) -> tuple[str, dict[str, Any]]:
    """Normalise a Postgres URL for asyncpg, including Supabase's pooler.

    - Supabase's transaction pooler (port 6543, or `pgbouncer=true`) does not
      keep prepared statements between transactions, so asyncpg's statement
      cache must be off. The session pooler (port 5432) needs no change.
    - `pgbouncer=true` is a Prisma-style flag asyncpg would reject; it is removed.
    - Remote hosts get TLS unless the URL already sets `sslmode`.
    """
    parts = urlsplit(dsn)
    params = parse_qsl(parts.query, keep_blank_values=True)
    pgbouncer = any(key == "pgbouncer" and value.lower() in {"1", "true"} for key, value in params)
    params = [(key, value) for key, value in params if key != "pgbouncer"]
    options: dict[str, Any] = {}
    if pgbouncer or parts.port == 6543:
        options["statement_cache_size"] = 0
    host = (parts.hostname or "").lower()
    if host and host not in LOCAL_HOSTS and "sslmode" not in {key for key, _ in params}:
        options["ssl"] = "require"
    cleaned = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(params), parts.fragment))
    return cleaned, options


def storage_status() -> str:
    """"not_configured", "connected", or "unreachable" (configured but no pool)."""
    if not DATABASE_URL:
        return "not_configured"
    return "connected" if _pool is not None else "unreachable"


async def init_storage() -> None:
    """Connect and create tables. A database outage never stops the API starting.

    Free hosted databases (for example Supabase's free plan) can be paused or
    briefly unreachable; the assistant and public pages still work without
    storage, and `ensure_storage()` retries later.
    """
    global _pool, _last_attempt, _last_error
    if not DATABASE_URL or asyncpg is None or _pool is not None:
        return
    _last_attempt = time.monotonic()
    dsn, options = connection_options(DATABASE_URL)
    try:
        pool = await asyncpg.create_pool(
            dsn, min_size=1, max_size=3, command_timeout=10, timeout=CONNECT_TIMEOUT_SECONDS, **options,
        )
    except Exception as exc:  # network, auth, paused project: report, don't crash
        _last_error = type(exc).__name__
        # Never log the URL: it contains the database password.
        logger.warning("Database unavailable (%s); continuing without storage", _last_error)
        return
    try:
        await _create_schema(pool)
    except Exception:
        await pool.close()
        raise
    _pool = pool
    _last_error = ""
    await purge_expired()


async def ensure_storage() -> None:
    """Retry a failed connection, at most once per RECONNECT_INTERVAL_SECONDS."""
    if _pool is None and DATABASE_URL and time.monotonic() - _last_attempt >= RECONNECT_INTERVAL_SECONDS:
        await init_storage()


async def _create_schema(pool) -> None:
    async with pool.acquire() as connection:
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
            CREATE TABLE IF NOT EXISTS portfolio_agent_sessions (
              session_id TEXT PRIMARY KEY, messages JSONB NOT NULL DEFAULT '[]'::jsonb,
              updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS portfolio_answer_cache (
              cache_key TEXT PRIMARY KEY, response JSONB NOT NULL,
              hits INTEGER NOT NULL DEFAULT 0,
              created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS portfolio_events_created_idx
              ON portfolio_events (created_at, name);
            CREATE TABLE IF NOT EXISTS portfolio_match_shares (
              share_id TEXT PRIMARY KEY, result JSONB NOT NULL,
              created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS portfolio_testimonials (
              id BIGSERIAL PRIMARY KEY, name TEXT NOT NULL, role TEXT NOT NULL,
              relationship TEXT NOT NULL, quote TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'pending',
              created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), reviewed_at TIMESTAMPTZ
            );
        """)
        # Deny Supabase's public REST/GraphQL API (anon and authenticated roles):
        # with RLS on and no policies, only the owning role can read or write.
        await connection.execute(";".join(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY" for table in TABLES))


async def purge_expired() -> dict[str, int]:
    """Data retention: drop chat sessions and cached answers past their window.

    Conversations are visitor content, so they are not kept indefinitely.
    Runs at startup; long-lived deployments restart often enough on Render.
    """
    if _pool is None:
        return {}
    sessions = await _pool.execute(
        "DELETE FROM portfolio_agent_sessions WHERE updated_at < NOW() - make_interval(days => $1)",
        SESSION_RETENTION_DAYS,
    )
    answers = await _pool.execute(
        "DELETE FROM portfolio_answer_cache WHERE created_at < NOW() - make_interval(days => $1)",
        ANSWER_CACHE_DAYS,
    )
    shares = await _pool.execute(
        "DELETE FROM portfolio_match_shares WHERE created_at < NOW() - make_interval(days => $1)",
        SHARE_RETENTION_DAYS,
    )
    errors = await _pool.execute(
        "DELETE FROM portfolio_events WHERE name = 'client_error' AND created_at < NOW() - INTERVAL '30 days'",
    )
    # asyncpg returns command tags such as "DELETE 3".
    count = lambda tag: int(tag.split()[-1])  # noqa: E731
    return {"sessions": count(sessions), "answers": count(answers), "shares": count(shares), "client_errors": count(errors)}


# ── Job-match share links ────────────────────────────────────────────────────
async def save_match_share(share_id: str, result: dict[str, Any]) -> None:
    await _require_pool().execute(
        "INSERT INTO portfolio_match_shares(share_id,result) VALUES($1,$2::jsonb)",
        share_id, json.dumps(result),
    )


async def load_match_share(share_id: str) -> dict[str, Any] | None:
    value = await _require_pool().fetchval(
        "SELECT result FROM portfolio_match_shares WHERE share_id=$1 "
        "AND created_at >= NOW() - make_interval(days => $2)",
        share_id, SHARE_RETENTION_DAYS,
    )
    if isinstance(value, str):
        value = json.loads(value)
    return value if isinstance(value, dict) else None


# ── Testimonials (moderated) ─────────────────────────────────────────────────
async def save_testimonial(name: str, role: str, relationship: str, quote: str) -> int:
    return await _require_pool().fetchval(
        "INSERT INTO portfolio_testimonials(name,role,relationship,quote) VALUES($1,$2,$3,$4) RETURNING id",
        name, role, relationship, quote,
    )


async def list_testimonials(status: str | None = None) -> list[dict[str, Any]]:
    query = "SELECT id,name,role,relationship,quote,status,created_at FROM portfolio_testimonials"
    rows = (
        await _require_pool().fetch(query + " WHERE status=$1 ORDER BY created_at DESC LIMIT 100", status)
        if status else await _require_pool().fetch(query + " ORDER BY created_at DESC LIMIT 100")
    )
    return [dict(row) for row in rows]


async def set_testimonial_status(testimonial_id: int, status: str) -> bool:
    tag = await _require_pool().execute(
        "UPDATE portfolio_testimonials SET status=$2, reviewed_at=NOW() WHERE id=$1",
        testimonial_id, status,
    )
    return tag.endswith(" 1")


# ── Newsletter recipients and client errors ──────────────────────────────────
async def list_subscribers() -> list[str]:
    rows = await _require_pool().fetch("SELECT email FROM portfolio_subscribers ORDER BY created_at")
    return [row["email"] for row in rows]


async def delete_subscriber(email: str) -> None:
    await _require_pool().execute("DELETE FROM portfolio_subscribers WHERE email=$1", email.lower())


async def recent_client_errors(limit: int = 50) -> list[dict[str, Any]]:
    rows = await _require_pool().fetch(
        "SELECT path, properties, created_at FROM portfolio_events WHERE name='client_error' "
        "ORDER BY created_at DESC LIMIT $1",
        limit,
    )
    result = []
    for row in rows:
        properties = row["properties"]
        if isinstance(properties, str):
            properties = json.loads(properties)
        result.append({"path": row["path"], "created_at": row["created_at"], **(properties or {})})
    return result


async def close_storage() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


def connected() -> bool:
    return _pool is not None


async def ping(timeout: float = 2.0) -> str:
    """Return "connected", "not_configured", or "unreachable" for health checks.

    Also the reconnect hook: the frontend probes /api/health on every visit, so a
    database that was down at startup is picked up again without a restart.
    """
    await ensure_storage()
    if _pool is None:
        return storage_status()
    try:
        await asyncio.wait_for(_pool.fetchval("SELECT 1"), timeout=timeout)
        return "connected"
    except Exception:
        return "unreachable"


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
    value = await _pool.fetchval(
        "SELECT content FROM portfolio_content_revisions ORDER BY id DESC LIMIT 1"
    )
    return json.loads(value) if isinstance(value, str) else value


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


FUNNEL_STAGES: dict[str, tuple[str, ...]] = {
    "visits": ("page_view",),
    "case_studies": ("case_study_view",),
    "resume": ("resume_view", "resume_download"),
    "job_match": ("job_match_run",),
    "contact": ("contact_success",),
}


async def funnel_summary(days: int) -> dict[str, Any]:
    """Daily counts per funnel stage plus the most-viewed case studies."""
    pool = _require_pool()
    names = sorted({name for group in FUNNEL_STAGES.values() for name in group})
    rows = await pool.fetch(
        """
        SELECT date_trunc('day', created_at)::date AS day, name, COUNT(*) AS count
        FROM portfolio_events
        WHERE created_at >= NOW() - make_interval(days => $1) AND name = ANY($2::text[])
        GROUP BY day, name ORDER BY day
        """,
        days, names,
    )
    top = await pool.fetch(
        """
        SELECT properties->>'project' AS project, COUNT(*) AS count
        FROM portfolio_events
        WHERE created_at >= NOW() - make_interval(days => $1)
          AND name = 'case_study_view' AND properties ? 'project'
        GROUP BY project ORDER BY count DESC LIMIT 8
        """,
        days,
    )
    stage_of = {name: stage for stage, group in FUNNEL_STAGES.items() for name in group}
    daily: dict[str, dict[str, int]] = {}
    totals = dict.fromkeys(FUNNEL_STAGES, 0)
    for row in rows:
        stage = stage_of[row["name"]]
        day = row["day"].isoformat()
        bucket = daily.setdefault(day, dict.fromkeys(FUNNEL_STAGES, 0))
        bucket[stage] += row["count"]
        totals[stage] += row["count"]
    return {
        "days": days,
        "stages": list(FUNNEL_STAGES),
        "totals": totals,
        "daily": [{"day": day, **counts} for day, counts in sorted(daily.items())],
        "top_case_studies": [dict(row) for row in top],
    }


async def get_cached_answer(cache_key: str, max_age_days: int) -> dict[str, Any] | None:
    if not _pool:
        return None
    value = await _pool.fetchval(
        """
        UPDATE portfolio_answer_cache SET hits = hits + 1
        WHERE cache_key=$1 AND created_at >= NOW() - make_interval(days => $2)
        RETURNING response
        """,
        cache_key, max_age_days,
    )
    if isinstance(value, str):
        value = json.loads(value)
    return value if isinstance(value, dict) else None


async def save_cached_answer(cache_key: str, response: dict[str, Any]) -> None:
    if not _pool:
        return
    await _pool.execute(
        """
        INSERT INTO portfolio_answer_cache(cache_key,response) VALUES($1,$2::jsonb)
        ON CONFLICT(cache_key) DO UPDATE SET response=EXCLUDED.response, created_at=NOW(), hits=0
        """,
        cache_key, json.dumps(response),
    )


async def delete_agent_session(session_id: str) -> bool:
    if not _pool:
        return False
    await _pool.execute("DELETE FROM portfolio_agent_sessions WHERE session_id=$1", session_id)
    return True


async def load_agent_session(session_id: str) -> list[dict[str, str]] | None:
    if not _pool:
        return None
    value = await _pool.fetchval(
        "SELECT messages FROM portfolio_agent_sessions WHERE session_id=$1",
        session_id,
    )
    if isinstance(value, str):
        value = json.loads(value)
    return list(value) if isinstance(value, list) else None


async def save_agent_session(session_id: str, messages: list[dict[str, str]]) -> bool:
    if not _pool:
        return False
    await _pool.execute(
        """
        INSERT INTO portfolio_agent_sessions(session_id,messages,updated_at)
        VALUES($1,$2::jsonb,NOW())
        ON CONFLICT(session_id) DO UPDATE SET messages=EXCLUDED.messages, updated_at=NOW()
        """,
        session_id,
        json.dumps(messages),
    )
    return True
