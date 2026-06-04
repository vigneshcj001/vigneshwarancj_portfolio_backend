from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import MAX_BODY_BYTES


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
        if content_length and int(content_length) > MAX_BODY_BYTES:
            return JSONResponse(status_code=413, content={"detail": "Request too large"})

        # Slow-path: read actual bytes to catch chunked / no-Content-Length requests
        body_bytes = b""
        async for chunk in request.stream():
            body_bytes += chunk
            if len(body_bytes) > MAX_BODY_BYTES:
                return JSONResponse(status_code=413, content={"detail": "Request too large"})

        # Re-inject the consumed body so downstream handlers can read it
        async def _replay():
            return {"type": "http.request", "body": body_bytes, "more_body": False}

        request._receive = _replay  # type: ignore[attr-defined]
        return await call_next(request)
