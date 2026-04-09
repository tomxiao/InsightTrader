from __future__ import annotations

import uvicorn

from ta_service.app.factory import create_app
from ta_service.config.settings import get_settings


app = create_app()


def run() -> None:
    settings = get_settings()
    uvicorn.run(
        "ta_service.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.environment == "development",
    )


if __name__ == "__main__":
    run()
