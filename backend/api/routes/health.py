from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter
from sqlalchemy import text

from api.deps import DBSession

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(db: DBSession) -> dict[str, Any]:
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        logger.exception("DB health check failed")

    # TODO: query a crawler_runs table and return per-crawler last_run timestamps.
    return {
        "status": "ok",
        "db": db_ok,
        "last_crawl": {
            "clever": None,
            "spirii": None,
            "monta": None,
        },
    }
