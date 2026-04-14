"""LennyVerse — FastAPI application."""
import logging
import sys

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.config import config
from app.rate_limit import limiter
from app.routers.graph import router as graph_router
from app.routers.explore import router as explore_router
from app.routers.ingest import router as ingest_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    if not config.anthropic_api_key:
        if config.is_production:
            logger.error("ANTHROPIC_API_KEY is not set in production. Exiting.")
            sys.exit(1)
        logger.warning("ANTHROPIC_API_KEY not set — explore and ingest endpoints will be unavailable")

    app = FastAPI(
        title="LennyVerse",
        description="The living knowledge graph of product management wisdom",
        version="1.0.0",
        docs_url="/docs" if not config.is_production else None,
        redoc_url=None,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins if config.is_production else ["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(
        ProxyHeadersMiddleware,
        trusted_hosts=["127.0.0.1", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"],
    )

    @app.exception_handler(Exception)
    async def global_error_handler(request: Request, exc: Exception):
        logger.error("Unhandled error: %s: %s", type(exc).__name__, exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "detail": "Something went wrong. Please try again."},
        )

    @app.get("/health")
    async def health():
        wiki_exists = config.wiki_path.exists()
        concept_count = len(list((config.wiki_path / "concepts").glob("*.md"))) if wiki_exists else 0
        return {
            "status": "ok" if concept_count > 0 else "empty",
            "service": "lennyverse",
            "wiki_path": str(config.wiki_path),
            "concept_count": concept_count,
            "llm_configured": bool(config.anthropic_api_key),
        }

    app.include_router(graph_router)
    app.include_router(explore_router)
    app.include_router(ingest_router)

    logger.info(
        "LennyVerse started — env=%s, wiki=%s, llm=%s",
        config.environment, config.wiki_path, "anthropic" if config.anthropic_api_key else "none",
    )
    return app


app = create_app()
