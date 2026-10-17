from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.ai.okf import load_bundle
from app.config import ALLOWED_ORIGINS
from app.limiter import limiter
from app.middleware import RequestSizeLimitMiddleware, SecurityHeadersMiddleware
from app.routes.assistant import router
from app.routes.resume import router as resume_router
from app.routes.platform import router as platform_router
from app.services.storage import close_storage, init_storage

app = FastAPI(
    title="Vigneshwaran Portfolio Assistant API",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Middleware (outermost → innermost: CORS, security headers, size limit)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["Content-Type", "X-Admin-Key"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestSizeLimitMiddleware)

# Routes
app.include_router(router)
app.include_router(resume_router)
app.include_router(platform_router)


@app.on_event("startup")
async def startup_platform_storage():
    load_bundle()  # Fail fast when committed OKF index or documents are invalid.
    await init_storage()


@app.on_event("shutdown")
async def shutdown_platform_storage():
    await close_storage()
