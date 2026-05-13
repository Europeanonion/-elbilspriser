from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import health, prices, stations
from db.session import init_engine, dispose_engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Starting up — initialising DB engine")
    await init_engine()
    yield
    logger.info("Shutting down — disposing DB engine")
    await dispose_engine()


app = FastAPI(
    title="Elbilspriser API",
    version="0.1.0",
    lifespan=lifespan,
)

# Tighten allowed origins once a frontend domain is known.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(prices.router, prefix="/api/v1")
app.include_router(stations.router, prefix="/api/v1")
