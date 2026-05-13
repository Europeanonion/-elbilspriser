"""Clever charging station crawler — Playwright (Chromium headless).

TODO: The actual JSON endpoint must be reverse-engineered from clever.dk/ladekort.
      Open DevTools → Network tab → filter XHR/fetch while the map loads, then
      update CLEVER_MAP_URL in .env with the real URL and adjust _parse_station()
      to match the actual response schema.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from playwright.async_api import Route, async_playwright

from crawlers.base import BaseCrawler
from db.models import PriceSnapshot, Station

logger = logging.getLogger(__name__)

_CLEVER_MAP_URL: str = os.environ.get("CLEVER_MAP_URL", "https://clever.dk/ladekort")
_OPERATOR_ID = 1  # internal ID assigned to Clever


class CleverCrawler(BaseCrawler):
    name = "clever"

    def __init__(self) -> None:
        self._intercepted: list[dict] = []

    async def fetch(self) -> list[dict]:
        self._intercepted = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            async def _handle_route(route: Route) -> None:
                response = await route.fetch()
                try:
                    body = await response.json()
                    if isinstance(body, list) and body:
                        self._intercepted.extend(body)
                    elif isinstance(body, dict) and ("stations" in body or "locations" in body):
                        key = "stations" if "stations" in body else "locations"
                        self._intercepted.extend(body[key])
                except Exception:
                    pass
                await route.fulfill(response=response)

            # Intercept any JSON response that looks like station data.
            await page.route("**/*", _handle_route)

            try:
                await page.goto(_CLEVER_MAP_URL, wait_until="networkidle", timeout=60_000)
            except Exception as exc:
                logger.warning("Navigation error (non-fatal): %s", exc)

            if not self._intercepted:
                # Fallback: try to read data injected into the page's JS context.
                logger.info("No XHR interception — trying page.evaluate fallback")
                try:
                    data = await page.evaluate("() => window.__CLEVER_STATIONS__ ?? []")
                    if isinstance(data, list):
                        self._intercepted = data
                except Exception as exc:
                    logger.warning("page.evaluate fallback failed: %s", exc)

            await browser.close()

        logger.info("Clever: fetched %d raw records", len(self._intercepted))
        return self._intercepted

    async def parse(self, raw: list[dict]) -> list[PriceSnapshot]:
        now = datetime.now(timezone.utc)
        snapshots: list[PriceSnapshot] = []

        for record in raw:
            try:
                snapshot = _parse_station(record, now)
                if snapshot is not None:
                    snapshots.append(snapshot)
            except Exception as exc:
                logger.warning("Skipping unparseable record: %s — %s", exc, record)

        return snapshots


def _parse_station(record: dict[str, Any], now: datetime) -> PriceSnapshot | None:
    """Map a raw Clever station dict to a PriceSnapshot.

    TODO: update field names once the real API schema is known.
    """
    price_kwh = record.get("pricePerKwh") or record.get("price_kwh")
    if price_kwh is None:
        return None

    import uuid

    station_id_raw = record.get("id") or record.get("stationId") or str(uuid.uuid4())

    return PriceSnapshot(
        time=now,
        # station_id must reference an existing stations row; a real implementation
        # should upsert the Station first and use its UUID.
        station_id=uuid.UUID(str(station_id_raw)) if _is_uuid(str(station_id_raw)) else uuid.uuid5(uuid.NAMESPACE_URL, str(station_id_raw)),
        operator_id=_OPERATOR_ID,
        price_kwh=price_kwh,
        price_min=record.get("pricePerMinute") or record.get("price_min"),
        session_fee=record.get("sessionFee") or record.get("session_fee"),
        currency=record.get("currency", "DKK"),
        source_raw=record,
    )


def _is_uuid(value: str) -> bool:
    import uuid as _uuid
    try:
        _uuid.UUID(value)
        return True
    except ValueError:
        return False


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    crawler = CleverCrawler()
    await crawler.run()


if __name__ == "__main__":
    asyncio.run(main())
