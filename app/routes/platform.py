import asyncio
import json
import secrets
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.config import ADMIN_API_KEY, DATABASE_URL, METADATA_CACHE_SECONDS
from app.limiter import limiter

try:
    import asyncpg
except ImportError:  # Local static validation can run before dependencies install.
    asyncpg = None

router = APIRouter()
DATA_PATH = Path(__file__).parent.parent.parent / "portfolio_data.json"
_pool = None
_proof_cache: dict[str, Any] = {"expires": 0, "value": None}


class EventPayload(BaseModel):
    name: str = Field(pattern=r"^[a-z0-9_]{2,64}$")
    path: str = Field(default="/", max_length=200)
    properties: dict[str, str | int | float | bool] = Field(default_factory=dict)

    @field_validator("properties")
    @classmethod
    def limit_properties(cls, value):
        if len(value) > 12:
            raise ValueError("too many properties")
        blocked = {"email", "phone", "message", "name", "content"}
        if blocked.intersection(key.lower() for key in value):
            raise ValueError("personal or message data is not accepted")
        return value


class ContactPayload(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    message: str = Field(min_length=10, max_length=2000)
    website: str = Field(default="", max_length=200)


class NewsletterPayload(BaseModel):
    email: EmailStr


class ContentPayload(BaseModel):
    content: dict[str, Any]
    note: str = Field(default="Portfolio content update", max_length=200)


class DemoPayload(BaseModel):
    input: str = Field(min_length=1, max_length=160)


async def init_platform_storage() -> None:
    global _pool
    if not DATABASE_URL or asyncpg is None:
        return
    _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=3, command_timeout=10)
    async with _pool.acquire() as conn:
        await conn.execute("""
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


async def close_platform_storage() -> None:
    if _pool:
        await _pool.close()


def _admin(key: str | None) -> None:
    if not ADMIN_API_KEY or not key or not secrets.compare_digest(key, ADMIN_API_KEY):
        raise HTTPException(status_code=401, detail="Valid admin key required")


def _require_db() -> None:
    if _pool is None:
        raise HTTPException(status_code=503, detail="Database storage is not configured")


def _fetch_json(url: str) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": "vigneshwaran-portfolio/1.0", "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=8) as response:
        return json.load(response)


async def _proof() -> dict[str, Any]:
    now = time.time()
    if _proof_cache["value"] and _proof_cache["expires"] > now:
        return _proof_cache["value"]
    try:
        repos, pypi = await asyncio.gather(
            asyncio.to_thread(_fetch_json, "https://api.github.com/users/vigneshcj001/repos?sort=updated&per_page=6"),
            asyncio.to_thread(_fetch_json, "https://pypi.org/pypi/glycanbench/json"),
        )
        value = {
            "github": [{"name": item["name"], "url": item["html_url"], "stars": item["stargazers_count"], "updated_at": item["updated_at"]} for item in repos[:6]],
            "pypi": {"version": pypi["info"]["version"], "url": pypi["info"]["package_url"]},
            "cached_at": datetime.now(timezone.utc).isoformat(),
        }
        _proof_cache.update(value=value, expires=now + METADATA_CACHE_SECONDS)
        return value
    except (urllib.error.URLError, TimeoutError, KeyError, ValueError) as exc:
        if _proof_cache["value"]:
            return _proof_cache["value"]
        raise HTTPException(status_code=503, detail="Public metadata temporarily unavailable") from exc


@router.get("/api/health")
async def detailed_health():
    return {"status": "ok", "database": "connected" if _pool else "not_configured", "time": datetime.now(timezone.utc).isoformat()}


@router.get("/api/proof")
@limiter.limit("30/minute")
async def public_proof(request: Request):
    return await _proof()


@router.post("/api/demo/{slug}")
@limiter.limit("10/minute")
async def project_demo(request: Request, slug: str, payload: DemoPayload):
    """Safe portfolio simulation. No employer systems, model calls, or private data."""
    text = payload.input.strip()
    if slug == "aiora":
        intent = "booking" if "book" in text.lower() else "storefront" if any(word in text.lower() for word in ("buy", "order", "product")) else "agent-menu"
        return {"simulation": True, "route": intent, "pipeline": ["gateway", "tenant-router", intent, "queued-reply"], "security": ["rate-limit", "HMAC webhook verification"]}
    if slug == "pocketpet":
        sensitive = any(word in text.lower() for word in ("pay", "password", "submit", "purchase"))
        return {"simulation": True, "task": text, "action": "approval_required" if sensitive else "preview_ready", "controls": ["pause", "cancel", "spend-limit", "secret-field-refusal"]}
    if slug == "glycanbench":
        return {"simulation": True, "input": text, "available_tools": ["format conversion", "descriptors", "fingerprints", "GLYSUM alignment", "MPNN prediction"], "notice": "Use live GlycanBench for scientific output."}
    raise HTTPException(status_code=404, detail="Demo not available")


@router.post("/api/events", status_code=202)
@limiter.limit("60/minute")
async def record_event(request: Request, payload: EventPayload):
    if _pool:
        await _pool.execute("INSERT INTO portfolio_events(name,path,properties) VALUES($1,$2,$3::jsonb)", payload.name, payload.path, json.dumps(payload.properties))
    return {"accepted": True}


@router.post("/api/contact", status_code=202)
@limiter.limit("5/hour")
async def contact(request: Request, payload: ContactPayload):
    if payload.website:  # Honeypot. Return success so bots get no tuning signal.
        return {"accepted": True}
    _require_db()
    await _pool.execute("INSERT INTO portfolio_contacts(name,email,message) VALUES($1,$2,$3)", payload.name, str(payload.email).lower(), payload.message)
    return {"accepted": True}


@router.post("/api/newsletter", status_code=202)
@limiter.limit("5/hour")
async def newsletter(request: Request, payload: NewsletterPayload):
    _require_db()
    await _pool.execute("INSERT INTO portfolio_subscribers(email) VALUES($1) ON CONFLICT(email) DO NOTHING", str(payload.email).lower())
    return {"accepted": True}


@router.get("/api/admin/content")
async def read_content(x_admin_key: str | None = Header(default=None)):
    _admin(x_admin_key)
    if _pool:
        latest = await _pool.fetchval("SELECT content FROM portfolio_content_revisions ORDER BY id DESC LIMIT 1")
        if latest:
            return latest
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


@router.put("/api/admin/content")
async def update_content(payload: ContentPayload, x_admin_key: str | None = Header(default=None)):
    _admin(x_admin_key)
    _require_db()
    revision_id = await _pool.fetchval("INSERT INTO portfolio_content_revisions(content,note) VALUES($1::jsonb,$2) RETURNING id", json.dumps(payload.content), payload.note)
    return {"saved": True, "revision_id": revision_id}


@router.get("/api/admin/analytics")
async def analytics(x_admin_key: str | None = Header(default=None)):
    _admin(x_admin_key)
    _require_db()
    rows = await _pool.fetch("SELECT name, COUNT(*) AS count, MAX(created_at) AS last_seen FROM portfolio_events GROUP BY name ORDER BY count DESC")
    return {"events": [dict(row) for row in rows]}


def _urls(value: Any):
    if isinstance(value, dict):
        for item in value.values():
            yield from _urls(item)
    elif isinstance(value, list):
        for item in value:
            yield from _urls(item)
    elif isinstance(value, str) and value.startswith("https://"):
        yield value


def _check_link(url: str) -> dict[str, Any]:
    try:
        request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "vigneshwaran-portfolio/1.0"})
        with urllib.request.urlopen(request, timeout=8) as response:
            return {"url": url, "status": response.status, "ok": response.status < 400}
    except Exception as exc:
        return {"url": url, "status": None, "ok": False, "error": str(exc)[:160]}


@router.post("/api/admin/check-links")
async def check_links(x_admin_key: str | None = Header(default=None)):
    _admin(x_admin_key)
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    urls = sorted(set(_urls(data)))[:100]
    results = await asyncio.gather(*(asyncio.to_thread(_check_link, url) for url in urls))
    return {"checked": len(results), "failed": [item for item in results if not item["ok"]]}


@router.get("/api/og/{slug}.svg")
async def project_og(slug: str):
    title = slug.replace("-", " ").title()[:70]
    safe = title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630"><defs><linearGradient id="g"><stop stop-color="#0f172a"/><stop offset="1" stop-color="#1d4ed8"/></linearGradient></defs><rect width="1200" height="630" fill="url(#g)"/><text x="72" y="110" fill="#93c5fd" font-family="Arial" font-size="28" font-weight="700">VIGNESHWARAN C. J. · CASE STUDY</text><text x="72" y="300" fill="white" font-family="Arial" font-size="70" font-weight="800">{safe}</text><text x="72" y="410" fill="#cbd5e1" font-family="Arial" font-size="32">Engineering · AI · Research</text></svg>'''
    return Response(svg, media_type="image/svg+xml", headers={"Cache-Control": "public, max-age=86400"})
