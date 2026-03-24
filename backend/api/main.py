import os
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app_mode = os.getenv("RAG_APP_MODE", "full").strip().lower()
is_smoke_mode = app_mode == "smoke"
enable_routers = os.getenv("RAG_ENABLE_ROUTERS", "true").strip().lower() in {
    "1",
    "true",
    "yes",
}

# Do not require settings import when running smoke diagnostics.
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
if not is_smoke_mode:
    try:
        from backend.config.settings import settings

        frontend_url = settings.FRONTEND_URL
    except Exception as exc:
        logger.warning("Settings import failed; using FRONTEND_URL env fallback: %s", exc)


def _normalize_origin(url: str) -> str:
    return url.strip().rstrip("/")


def _parse_frontend_origins(primary_url: str) -> list[str]:
    # Allow a single URL in FRONTEND_URL and optional comma-separated extras in FRONTEND_URLS.
    candidates = [
        "http://localhost:5173",
        "http://localhost:3000",
        primary_url,
    ]
    extra_urls = os.getenv("FRONTEND_URLS", "")
    if extra_urls:
        candidates.extend(extra_urls.split(","))

    normalized: list[str] = []
    seen: set[str] = set()
    for raw in candidates:
        origin = _normalize_origin(raw)
        if origin and origin not in seen:
            normalized.append(origin)
            seen.add(origin)
    return normalized


allowed_origins = _parse_frontend_origins(frontend_url)
logger.info("Configured CORS allow_origins: %s", allowed_origins)

app = FastAPI(
    title="RAG API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global error handler — never expose stack traces to client
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)[:200]},
    )


# Routes (optional for startup diagnostics)
if not is_smoke_mode and enable_routers:
    from backend.api.routes import ingest, documents, query

    app.include_router(ingest.router, prefix="/api", tags=["ingestion"])
    app.include_router(documents.router, prefix="/api", tags=["documents"])
    app.include_router(query.router, prefix="/api", tags=["query"])
else:
    logger.info(
        "API routers disabled (RAG_APP_MODE=%s, RAG_ENABLE_ROUTERS=%s)",
        app_mode,
        enable_routers,
    )


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "mode": app_mode,
        "routers_enabled": (not is_smoke_mode and enable_routers),
    }
