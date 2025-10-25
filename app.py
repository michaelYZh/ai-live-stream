from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.audio import router as audio_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Live Stream Backend",
        version="0.1.0",
        description="Prototype backend.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(audio_router)

    @app.get("/healthz", tags=["health"])
    async def healthcheck():
        return {"status": "ok"}

    return app


app = create_app()
