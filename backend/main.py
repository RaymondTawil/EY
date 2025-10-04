# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import settings
from backend.db.session import init_db
from backend.api.endpoints import scoring, applications, advice, review

def create_app() -> FastAPI:
    app = FastAPI(title="AI Credit Risk API", version="1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    # Routers (versioned)
    app.include_router(scoring.router, prefix=settings.API_V1_STR)
    app.include_router(applications.router, prefix=settings.API_V1_STR)
    app.include_router(advice.router, prefix=settings.API_V1_STR)
    app.include_router(review.router, prefix=settings.API_V1_STR)

    @app.on_event("startup")
    def on_startup():
        init_db()

    return app

app = create_app()
