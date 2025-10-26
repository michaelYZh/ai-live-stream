from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from typing import AsyncIterator, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import PROCESSOR_LOOP_INTERVAL
from routers.audio import router as audio_router
from routers.messages import router as messages_router
from services.processor import StreamProcessor

if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown hooks."""

    processor = StreamProcessor()
    stop_event = asyncio.Event()
    worker_task: Optional[asyncio.Task[None]] = None

    async def run_processor() -> None:
        while not stop_event.is_set():
            try:
                await asyncio.to_thread(processor.process_once)
            except asyncio.CancelledError:
                break
            except Exception:  # pragma: no cover - logging only
                logger.exception("Stream processor loop encountered an error")
                await asyncio.sleep(1.0)
                continue

            await asyncio.sleep(PROCESSOR_LOOP_INTERVAL)

    worker_task = asyncio.create_task(run_processor(), name="stream-processor-worker")

    try:
        yield
    finally:
        stop_event.set()
        if worker_task:
            worker_task.cancel()
            with suppress(asyncio.CancelledError):
                await worker_task


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Live Stream Backend",
        version="0.1.0",
        description="Prototype backend.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(audio_router)
    app.include_router(messages_router)

    @app.get("/healthz", tags=["health"])
    async def healthcheck():
        return {"status": "ok"}

    return app


app = create_app()
