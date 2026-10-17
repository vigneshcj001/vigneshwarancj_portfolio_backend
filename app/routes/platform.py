import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import Response

from app.config import ADMIN_API_KEY, LAYA_API_KEY
from app.content import load_portfolio
from app.limiter import limiter
from app.schemas.platform import ContentPayload, ContactPayload, DemoPayload, EventPayload, NewsletterPayload
from app.services.demos import simulate_project
from app.services.proof import MetadataUnavailable, check_links as check_content_links, public_metadata
from app.services.storage import (
    StorageUnavailable,
    analytics_summary,
    connected,
    latest_content,
    record_event as store_event,
    save_contact,
    save_content_revision,
    save_subscriber,
)

router = APIRouter()


def _admin(key: str | None) -> None:
    if not ADMIN_API_KEY or not key or not secrets.compare_digest(key, ADMIN_API_KEY):
        raise HTTPException(status_code=401, detail="Valid admin key required")


def _storage_error(error: StorageUnavailable):
    raise HTTPException(status_code=503, detail=str(error)) from error


@router.get("/api/health")
async def detailed_health():
    return {
        "status": "ok",
        "database": "connected" if connected() else "not_configured",
        "assistant": {
            "knowledge": "okf",
            "router": "laya" if LAYA_API_KEY else "local_fallback",
            "generator": "groq",
        },
        "time": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/api/proof")
@limiter.limit("30/minute")
async def public_proof(request: Request):
    try:
        return await public_metadata()
    except MetadataUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.post("/api/demo/{slug}")
@limiter.limit("10/minute")
async def project_demo(request: Request, slug: str, payload: DemoPayload):
    """Safe simulation. No employer systems, model calls, or private data."""
    try:
        return simulate_project(slug, payload.input)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Demo not available") from error


@router.post("/api/events", status_code=202)
@limiter.limit("60/minute")
async def record_event(request: Request, payload: EventPayload):
    await store_event(payload.name, payload.path, payload.properties)
    return {"accepted": True}


@router.post("/api/contact", status_code=202)
@limiter.limit("5/hour")
async def contact(request: Request, payload: ContactPayload):
    if payload.website:
        return {"accepted": True}
    try:
        await save_contact(payload.name, str(payload.email), payload.message)
    except StorageUnavailable as error:
        _storage_error(error)
    return {"accepted": True}


@router.post("/api/newsletter", status_code=202)
@limiter.limit("5/hour")
async def newsletter(request: Request, payload: NewsletterPayload):
    try:
        await save_subscriber(str(payload.email))
    except StorageUnavailable as error:
        _storage_error(error)
    return {"accepted": True}


@router.get("/api/admin/content")
async def read_content(x_admin_key: str | None = Header(default=None)):
    _admin(x_admin_key)
    return await latest_content() or load_portfolio()


@router.put("/api/admin/content")
async def update_content(payload: ContentPayload, x_admin_key: str | None = Header(default=None)):
    _admin(x_admin_key)
    try:
        revision_id = await save_content_revision(payload.content, payload.note)
    except StorageUnavailable as error:
        _storage_error(error)
    return {"saved": True, "revision_id": revision_id}


@router.get("/api/admin/analytics")
async def analytics(x_admin_key: str | None = Header(default=None)):
    _admin(x_admin_key)
    try:
        events = await analytics_summary()
    except StorageUnavailable as error:
        _storage_error(error)
    return {"events": events}


@router.post("/api/admin/check-links")
async def check_links(x_admin_key: str | None = Header(default=None)):
    _admin(x_admin_key)
    results = await check_content_links(load_portfolio())
    return {"checked": len(results), "failed": [item for item in results if not item["ok"]]}


@router.get("/api/og/{slug}.svg")
async def project_og(slug: str):
    title = slug.replace("-", " ").title()[:70]
    safe = title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630"><defs><linearGradient id="g"><stop stop-color="#0f172a"/><stop offset="1" stop-color="#1d4ed8"/></linearGradient></defs><rect width="1200" height="630" fill="url(#g)"/><text x="72" y="110" fill="#93c5fd" font-family="Arial" font-size="28" font-weight="700">VIGNESHWARAN C. J. · CASE STUDY</text><text x="72" y="300" fill="white" font-family="Arial" font-size="70" font-weight="800">{safe}</text><text x="72" y="410" fill="#cbd5e1" font-family="Arial" font-size="32">Engineering · AI · Research</text></svg>'''
    return Response(svg, media_type="image/svg+xml", headers={"Cache-Control": "public, max-age=86400"})
