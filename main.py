import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.ai.okf import load_bundle
from app.config import ALLOWED_ORIGINS
from app.limiter import limiter
from app.middleware import RequestContextMiddleware, RequestSizeLimitMiddleware, SecurityHeadersMiddleware
from app.routes.assistant import router
from app.routes.resume import router as resume_router
from app.routes.platform import router as platform_router
from app.routes.translation import router as translation_router
from app.services.storage import close_storage, init_storage

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("portfolio")

RATE_LIMIT_MESSAGE = "Too many requests — please wait a moment and try again."


@asynccontextmanager
async def lifespan(_: FastAPI):
    load_bundle()  # Fail fast when committed OKF index or documents are invalid.
    await init_storage()
    try:
        yield
    finally:
        await close_storage()


app = FastAPI(
    title="Vigneshwaran Portfolio Assistant API",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)

app.state.limiter = limiter


def _retry_after_seconds(exc: RateLimitExceeded) -> int:
    try:
        return max(1, int(exc.limit.limit.get_expiry()))
    except Exception:  # pragma: no cover - defensive; slowapi internals vary
        return 60


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    # Use the same {"detail": str} shape as every other API error so the
    # frontend can show a readable message instead of "Request failed: 429".
    return JSONResponse(
        status_code=429,
        content={"detail": RATE_LIMIT_MESSAGE},
        headers={"Retry-After": str(_retry_after_seconds(exc))},
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", None)
    logger.exception("Unhandled error request_id=%s path=%s", request_id, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Something went wrong on our side. Please try again.", "request_id": request_id},
    )


# Middleware (outermost → innermost: CORS, request context, security headers, size limit)
app.add_middleware(RequestSizeLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["Content-Type", "X-Admin-Key"],
    expose_headers=["Retry-After", "X-Request-ID"],
    max_age=600,
)

# Routes
app.include_router(router)
app.include_router(resume_router)
app.include_router(platform_router)
app.include_router(translation_router)
