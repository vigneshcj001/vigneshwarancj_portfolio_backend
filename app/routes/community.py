"""Sharing, testimonials, newsletter delivery, client errors, and AI metrics."""

import html
import re
import secrets

from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse

from app.config import ADMIN_API_KEY
from app.limiter import limiter
from app.schemas.platform import (
    ClientErrorPayload,
    MatchSharePayload,
    NewsletterSendPayload,
    TestimonialPayload,
    TestimonialReview,
)
from app.services import newsletter, telemetry
from app.services.storage import (
    StorageUnavailable,
    delete_subscriber,
    list_subscribers,
    list_testimonials,
    load_match_share,
    recent_client_errors,
    record_event,
    save_match_share,
    save_testimonial,
    set_testimonial_status,
)

router = APIRouter()
_SHARE_ID = re.compile(r"^[A-Za-z0-9_-]{10,24}$")


def _admin(key: str | None) -> None:
    if not ADMIN_API_KEY or not key or not secrets.compare_digest(key, ADMIN_API_KEY):
        raise HTTPException(status_code=401, detail="Valid admin key required")


def _unavailable(error: StorageUnavailable):
    raise HTTPException(status_code=503, detail="This feature needs the database, which is not configured.") from error


# ── Job-match share links ────────────────────────────────────────────────────
@router.post("/api/match/share", status_code=201)
@limiter.limit("10/hour")
async def share_match(request: Request, payload: MatchSharePayload):
    """Store a match *result* for 30 days. The job description is never stored."""
    share_id = secrets.token_urlsafe(9)
    try:
        await save_match_share(share_id, payload.model_dump())
    except StorageUnavailable as error:
        _unavailable(error)
    return {"id": share_id, "expires_in_days": 30}


@router.get("/api/match/share/{share_id}")
@limiter.limit("60/minute")
async def get_shared_match(request: Request, share_id: str):
    if not _SHARE_ID.match(share_id):
        raise HTTPException(status_code=404, detail="This shared result does not exist or has expired.")
    try:
        result = await load_match_share(share_id)
    except StorageUnavailable as error:
        _unavailable(error)
    if result is None:
        raise HTTPException(status_code=404, detail="This shared result does not exist or has expired.")
    return result


# ── Testimonials ─────────────────────────────────────────────────────────────
@router.post("/api/testimonials", status_code=202)
@limiter.limit("3/hour")
async def submit_testimonial(request: Request, payload: TestimonialPayload):
    """Recommendations wait for the owner's approval before they are shown."""
    if payload.website:
        return {"accepted": True}
    try:
        await save_testimonial(payload.name.strip(), payload.role.strip(), payload.relationship.strip(), payload.quote.strip())
    except StorageUnavailable as error:
        _unavailable(error)
    return {"accepted": True}


@router.get("/api/testimonials")
@limiter.limit("60/minute")
async def approved_testimonials(request: Request):
    try:
        rows = await list_testimonials("approved")
    except StorageUnavailable:
        return {"testimonials": []}
    return {"testimonials": [
        {"name": row["name"], "role": row["role"], "relationship": row["relationship"], "quote": row["quote"]}
        for row in rows
    ]}


@router.get("/api/admin/testimonials")
async def admin_testimonials(status: str | None = Query(default=None, pattern=r"^(pending|approved|rejected)$"),
                             x_admin_key: str | None = Header(default=None)):
    _admin(x_admin_key)
    try:
        return {"testimonials": await list_testimonials(status)}
    except StorageUnavailable as error:
        _unavailable(error)


@router.put("/api/admin/testimonials/{testimonial_id}")
async def review_testimonial(testimonial_id: int, payload: TestimonialReview, x_admin_key: str | None = Header(default=None)):
    _admin(x_admin_key)
    try:
        updated = await set_testimonial_status(testimonial_id, payload.status)
    except StorageUnavailable as error:
        _unavailable(error)
    if not updated:
        raise HTTPException(status_code=404, detail="Testimonial not found")
    return {"id": testimonial_id, "status": payload.status}


# ── Newsletter delivery ──────────────────────────────────────────────────────
@router.post("/api/admin/newsletter/send")
async def send_newsletter(payload: NewsletterSendPayload, x_admin_key: str | None = Header(default=None)):
    _admin(x_admin_key)
    try:
        recipients = await list_subscribers()
    except StorageUnavailable as error:
        _unavailable(error)
    missing = newsletter.missing_settings()
    if payload.dry_run or missing:
        return {"dry_run": True, "recipients": len(recipients), "missing_settings": missing}
    report = await newsletter.send(payload.subject, payload.text, recipients)
    return {"dry_run": False, "attempted": report.attempted, "sent": report.sent, "failed": report.failed}


@router.get("/api/newsletter/unsubscribe", response_class=HTMLResponse)
@limiter.limit("20/minute")
async def unsubscribe(request: Request, email: str = Query(max_length=254), token: str = Query(max_length=64)):
    if not newsletter.valid_unsubscribe(email, token):
        return HTMLResponse(_page("This unsubscribe link is not valid."), status_code=400)
    try:
        await delete_subscriber(email)
    except StorageUnavailable as error:
        _unavailable(error)
    return HTMLResponse(_page(f"{html.escape(email)} has been unsubscribed. You will not receive further emails."))


def _page(message: str) -> str:
    return (
        "<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width'>"
        "<title>Newsletter</title><body style='font-family:system-ui;max-width:32rem;margin:4rem auto;padding:0 1rem'>"
        f"<p>{message}</p><p><a href='https://vigneshwarancj-portfolio-website.vercel.app/'>Back to the portfolio</a></p>"
    )


# ── Client error reports (first-party error monitoring) ──────────────────────
@router.post("/api/client-errors", status_code=202)
@limiter.limit("20/minute")
async def client_error(request: Request, payload: ClientErrorPayload):
    await record_event("client_error", payload.path, {
        "message": payload.message, "source": payload.source, "line": payload.line or 0, "kind": payload.kind,
    })
    return {"accepted": True}


@router.get("/api/admin/client-errors")
async def admin_client_errors(x_admin_key: str | None = Header(default=None)):
    _admin(x_admin_key)
    try:
        return {"errors": await recent_client_errors()}
    except StorageUnavailable as error:
        _unavailable(error)


# ── AI metrics ───────────────────────────────────────────────────────────────
@router.get("/api/admin/metrics")
async def ai_metrics(x_admin_key: str | None = Header(default=None)):
    _admin(x_admin_key)
    return telemetry.snapshot()
