from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from db.models import PriceSnapshot
from db.session import async_session_factory

logger = logging.getLogger(__name__)


class BaseCrawler(ABC):
    name: str = "base"

    @abstractmethod
    async def fetch(self) -> list[dict]:
        """Download raw data from the operator source."""
        ...

    @abstractmethod
    async def parse(self, raw: list[dict]) -> list[PriceSnapshot]:
        """Transform raw dicts into ORM instances ready for upsert."""
        ...

    async def _fetch_with_retry(self) -> list[dict]:
        # Exponential backoff: 2 s → 4 s → 8 s across three attempts.
        async for attempt in AsyncRetrying(
            retry=retry_if_exception_type(
                (httpx.TransportError, httpx.TimeoutException)
            ),
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=2, min=2, max=8),
            reraise=True,
        ):
            with attempt:
                return await self.fetch()
        raise RuntimeError("unreachable")  # satisfies type checker

    async def run(self) -> None:
        logger.info("[%s] crawl starting", self.name)
        t0 = time.monotonic()

        raw = await self._fetch_with_retry()
        snapshots = await self.parse(raw)

        async with async_session_factory() as session:
            session.add_all(snapshots)
            await session.commit()

        elapsed = time.monotonic() - t0
        logger.info(
            "[%s] crawl done — %d snapshots upserted in %.1fs",
            self.name,
            len(snapshots),
            elapsed,
        )
