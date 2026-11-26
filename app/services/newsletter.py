"""Newsletter delivery through Resend's HTTP API (optional).

Disabled until RESEND_API_KEY, NEWSLETTER_FROM, and UNSUBSCRIBE_SECRET are set.
Each recipient gets an individual email with a signed one-click unsubscribe
link, so one address can never unsubscribe another and no token table is needed.
"""

from __future__ import annotations

import hashlib
import hmac
import html
from dataclasses import dataclass
from urllib.parse import quote

import httpx

from app.config import NEWSLETTER_FROM, PUBLIC_API_URL, RESEND_API_KEY, UNSUBSCRIBE_SECRET

RESEND_URL = "https://api.resend.com/emails"


class NewsletterNotConfigured(RuntimeError):
    pass


@dataclass(frozen=True)
class SendReport:
    attempted: int
    sent: int
    failed: int


def missing_settings() -> list[str]:
    return [name for name, value in (
        ("RESEND_API_KEY", RESEND_API_KEY), ("NEWSLETTER_FROM", NEWSLETTER_FROM), ("UNSUBSCRIBE_SECRET", UNSUBSCRIBE_SECRET),
    ) if not value]


def unsubscribe_token(email: str) -> str:
    if not UNSUBSCRIBE_SECRET:
        raise NewsletterNotConfigured("UNSUBSCRIBE_SECRET is not set")
    return hmac.new(UNSUBSCRIBE_SECRET.encode(), email.lower().encode(), hashlib.sha256).hexdigest()[:32]


def valid_unsubscribe(email: str, token: str) -> bool:
    try:
        return hmac.compare_digest(unsubscribe_token(email), token)
    except NewsletterNotConfigured:
        return False


def unsubscribe_url(email: str) -> str:
    return f"{PUBLIC_API_URL}/api/newsletter/unsubscribe?email={quote(email)}&token={unsubscribe_token(email)}"


def render(text: str, email: str) -> tuple[str, str]:
    """Plain-text body is the source; HTML is escaped paragraphs plus the footer."""
    link = unsubscribe_url(email)
    footer = f"\n\n—\nYou subscribed at vigneshwarancj-portfolio-website.vercel.app.\nUnsubscribe: {link}"
    paragraphs = "".join(f"<p>{html.escape(block).replace(chr(10), '<br>')}</p>" for block in text.strip().split("\n\n"))
    body_html = (
        f"{paragraphs}<hr><p style=\"color:#64748b;font-size:12px\">You subscribed at the portfolio site. "
        f"<a href=\"{html.escape(link)}\">Unsubscribe</a></p>"
    )
    return text.strip() + footer, body_html


async def send(subject: str, text: str, recipients: list[str], client: httpx.AsyncClient | None = None) -> SendReport:
    missing = missing_settings()
    if missing:
        raise NewsletterNotConfigured(f"Set {', '.join(missing)} to send newsletters")
    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=15)
    sent = failed = 0
    try:
        for email in recipients:
            body_text, body_html = render(text, email)
            response = await client.post(RESEND_URL, headers={"Authorization": f"Bearer {RESEND_API_KEY}"}, json={
                "from": NEWSLETTER_FROM, "to": [email], "subject": subject, "text": body_text, "html": body_html,
                "headers": {"List-Unsubscribe": f"<{unsubscribe_url(email)}>"},
            })
            if response.status_code < 300:
                sent += 1
            else:
                failed += 1
    finally:
        if owns_client:
            await client.aclose()
    return SendReport(len(recipients), sent, failed)
