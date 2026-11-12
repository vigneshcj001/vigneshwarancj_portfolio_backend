from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import TRUSTED_PROXY_COUNT


def client_ip(request: Request) -> str:
    """Resolve the visitor's IP for rate limiting.

    Behind a reverse proxy (Render, Railway, Fly, nginx) the socket peer is the
    proxy, so every visitor would share one rate-limit bucket. Each trusted proxy
    appends the address it received the request from to X-Forwarded-For, so the
    real client is the entry ``TRUSTED_PROXY_COUNT`` positions from the right.
    Entries further left are client-controlled and are never trusted.
    """
    if TRUSTED_PROXY_COUNT > 0:
        forwarded = request.headers.get("x-forwarded-for", "")
        hops = [part.strip() for part in forwarded.split(",") if part.strip()]
        if len(hops) >= TRUSTED_PROXY_COUNT:
            return hops[-TRUSTED_PROXY_COUNT]
    return get_remote_address(request)


limiter = Limiter(key_func=client_ip, default_limits=["30/minute"])
