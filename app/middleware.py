import logging
import re
import time
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import MAX_BODY_BYTES

access_logger = logging.getLogger("portfolio.access")
_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{8,64}$")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Tag each request with an ID and log method, path, status, and latency.

    An incoming X-Request-ID (e.g. from Render's edge) is reused when it is
    well-formed so logs can be correlated across the proxy and the app.
    Request bodies, query strings, and IPs are deliberately not logged.
    """

    async def dispatch(self, request: Request, call_next):
        incoming = request.headers.get("x-request-id", "")
        request_id = incoming if _REQUEST_ID.match(incoming) else uuid.uuid4().hex[:16]
        request.state.request_id = request_id
        started = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started) * 1000
        response.headers["X-Request-ID"] = request_id
        if request.url.path not in ("/", "/api/health"):
            access_logger.info(
                "%s %s %s %.0fms id=%s",
                request.method, request.url.path, response.status_code, elapsed_ms, request_id,
            )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        # XSS auditor removed from modern browsers; setting to 0 prevents legacy exploitation
        response.headers["X-XSS-Protection"] = "0"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Fast-path: reject immediately when Content-Length header is present and too large
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > MAX_BODY_BYTES:
                    return JSONResponse(status_code=413, content={"detail": "Request too large"})
            except (ValueError, OverflowError):
                pass  # malformed header — fall through to slow-path byte counting

        # Slow-path: read actual bytes to catch chunked / no-Content-Length requests
        body_bytes = b""
        async for chunk in request.stream():
            body_bytes += chunk
            if len(body_bytes) > MAX_BODY_BYTES:
                return JSONResponse(status_code=413, content={"detail": "Request too large"})

        # Re-inject consumed body via the _body cache.
        # Setting _receive is not sufficient — Starlette's stream() checks
        # _stream_consumed before calling _receive and raises RuntimeError.
        # Setting _body makes body() / stream() return the cached bytes directly.
        request._body = body_bytes  # type: ignore[attr-defined]
        return await call_next(request)
