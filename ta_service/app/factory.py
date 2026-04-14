from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ta_service.api.routes.analysis import router as analysis_router
from ta_service.api.routes.admin_users import router as admin_users_router
from ta_service.api.routes.auth import router as auth_router
from ta_service.api.routes.conversations import router as conversations_router
from ta_service.api.routes.health import router as health_router
from ta_service.config.logging_config import setup_logging
from ta_service.config.settings import get_settings
from ta_service.db.mongo import create_mongo_client, get_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    mongo_client = create_mongo_client(settings)

    app.state.settings = settings
    app.state.mongo_client = mongo_client
    app.state.mongo_db = get_database(mongo_client, settings)

    try:
        yield
    finally:
        mongo_client.close()


def create_app() -> FastAPI:
    setup_logging()
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(settings.cors_origins),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.include_router(health_router)
    app.include_router(auth_router, prefix=settings.api_prefix)
    app.include_router(admin_users_router, prefix=settings.api_prefix)
    app.include_router(analysis_router, prefix=settings.api_prefix)
    app.include_router(conversations_router, prefix=settings.api_prefix)
    return app
