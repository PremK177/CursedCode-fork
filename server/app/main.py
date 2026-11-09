from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.exceptions import AppError, app_error_handler
from app.api.router import router

settings = get_settings()
setup_logging("DEBUG" if settings.is_development else "INFO")

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
)

# CORS — allow frontend origin
origins = list(set([settings.frontend_origin, "http://localhost:5173", "http://127.0.0.1:5173"]))
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppError, app_error_handler)

app.include_router(router)


@app.get("/")
async def root():
    return {
        "service": "DebugDojo API",
        "status": "ok",
        "frontend_url": "http://localhost:5173",
        "docs_url": "http://localhost:8000/docs",
        "endpoints": {
            "health": "/api/health",
            "challenges": "/api/challenges",
            "submit": "/api/submit",
            "hint": "/api/hint",
            "learner": "/api/learner/{learner_id}",
        },
    }


@app.on_event("startup")
async def on_startup():
    import logging
    logging.getLogger(__name__).info(
        "Debug Dojo API starting | env=%s | provider=%s",
        settings.app_env,
        settings.llm_provider,
    )
