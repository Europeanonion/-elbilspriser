"""Clever charging station crawler — Firebase Realtime Database via Playwright.

Clever's map (clever.dk/ladekort) loads station locations and dynamic per-station
prices from a Firebase Realtime Database. The data requires Firebase App Check
(reCAPTCHA Enterprise), so we cannot query it via the REST API directly — we must
load the real website in a headless browser and intercept the Firebase stream.

Firebase config discovered from the page:
  Project:  clever-app-prod
  RTDB URL: https://clever-app-prod-eu.europe-west1.firebasedatabase.app
  Paths:    v4-slim-locations (stations + prices), availability/V4 (EVSE status)

The Firebase SDK uses a WebSocket (wss://) connection for real-time sync.
We monitor that WebSocket for RTDB protocol messages containing location/price data.
An HTTP route handler covers the REST fallback path.

The first run should be executed with DEBUG logging to discover the exact field names
in the Firebase response schema, then _parse_record() can be tightened accordingly.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from playwright.async_api import Route, WebSocket, async_playwright

from crawlers.base import BaseCrawler
from db.models import PriceSnapshot, Station

logger = logging.getLogger(__name__)

_CLEVER_MAP_URL = "https://clever.dk/ladekort/"
_FIREBASE_RTDB_HOST = "clever-app-prod-eu.europe-west1.firebasedatabase.app"
_OPERATOR_ID = 1  # internal ID assigned to Clever


class CleverCrawler(BaseCrawler):
    name = "clever"

    def __init__(self) -> None:
        # locationId → raw record; populated by both WebSocket and HTTP handlers
        self._station_data: dict[str, dict] = {}

    async def fetch(self) -> list[dict]:
        self._station_data = {}

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )
            page = await context.new_page()

            # --- WebSocket monitor (primary path for Firebase RTDB) ---
            def _on_websocket(ws: WebSocket) -> None:
                if _FIREBASE_RTDB_HOST not in ws.url:
                    return
                logger.info("Firebase WebSocket opened: %s", ws.url[:100])

                def _on_frame(frame: Any) -> None:
                    try:
                        body = frame.body
                        text = body.decode("utf-8", errors="ignore") if isinstance(body, bytes) else body
                        _handle_firebase_message(text, self._station_data)
                    except Exception as exc:
                        logger.debug("WebSocket frame error: %s", exc)

                ws.on("framereceived", _on_frame)

            page.on("websocket", _on_websocket)

            # --- HTTP route handler (covers REST/SSE fallback) ---
            async def _on_firebase_http(route: Route) -> None:
                try:
                    response = await route.fetch()
                    body = await response.json()
                    if isinstance(body, dict) and body:
                        sample = list(body.keys())[:3]
                        if all(_is_uuid(k) for k in sample):
                            logger.info(
                                "Firebase HTTP: %d stations from %s",
                                len(body),
                                route.request.url[:120],
                            )
                            self._station_data.update(body)
                    await route.fulfill(response=response)
                except Exception as exc:
                    logger.debug("HTTP route handler error: %s", exc)
                    await route.continue_()

            await page.route(f"**/{_FIREBASE_RTDB_HOST}/**", _on_firebase_http)

            # Load the map and wait for Firebase to sync
            try:
                logger.info("Loading Clever map: %s", _CLEVER_MAP_URL)
                await page.goto(_CLEVER_MAP_URL, wait_until="networkidle", timeout=90_000)
            except Exception as exc:
                logger.warning("Page load timeout (checking collected data): %s", exc)

            # Extra wait for Firebase to deliver the initial snapshot
            await page.wait_for_timeout(8_000)

            # Fallback: extract station data from the Pinia store
            if not self._station_data:
                logger.info("No Firebase data intercepted — trying Pinia store fallback")
                try:
                    raw = await page.evaluate(
                        "() => { const p = window.__pinia; return p ? JSON.parse(JSON.stringify(p.state.value)) : null; }"
                    )
                    if isinstance(raw, dict):
                        logger.info("Pinia state keys: %s", list(raw.keys()))
                        logger.debug("Pinia state: %s", json.dumps(raw)[:2000])
                except Exception as exc:
                    logger.warning("Pinia fallback failed: %s", exc)

            await browser.close()

        count = len(self._station_data)
        logger.info("Clever: fetched %d station records", count)
        if count == 0:
            logger.warning(
                "No station data captured. Run with DEBUG logging to investigate. "
                "The Firebase schema or App Check mechanism may have changed."
            )
        return list(self._station_data.values())

    async def parse(self, raw: list[dict]) -> tuple[list[Station], list[PriceSnapshot]]:
        now = datetime.now(timezone.utc)
        stations: list[Station] = []
        snapshots: list[PriceSnapshot] = []

        for record in raw:
            logger.debug("Record keys: %s", list(record.keys()))
            try:
                station, snapshot = _parse_record(record, now)
                if station is not None and snapshot is not None:
                    stations.append(station)
                    snapshots.append(snapshot)
            except Exception as exc:
                logger.warning(
                    "Skipping unparseable record: %s — %s", exc, str(record)[:300]
                )

        logger.info(
            "Clever: parsed %d/%d records into station+snapshot pairs",
            len(snapshots),
            len(raw),
        )
        return stations, snapshots


# ---------------------------------------------------------------------------
# Firebase RTDB message parser
# ---------------------------------------------------------------------------

def _handle_firebase_message(text: str, station_data: dict[str, dict]) -> None:
    """Parse a Firebase RTDB WebSocket protocol message and extract station records."""
    msg = json.loads(text)
    if msg.get("t") != "d":
        return  # control message, not data

    d = msg.get("d", {})
    action = d.get("a")
    b = d.get("b", {})

    if action not in ("d", "p", "m") or not isinstance(b, dict):
        return

    path: str = b.get("p", "")
    data = b.get("d")

    if not isinstance(data, dict) or not data:
        return

    # Top-level dict with UUID keys → bulk location snapshot
    sample = list(data.keys())[:3]
    if all(_is_uuid(k) for k in sample):
        logger.info(
            "Firebase RTDB: action=%s path=%s count=%d", action, path, len(data)
        )
        station_data.update(data)
        return

    # Single-station update: path ends with a UUID
    path_parts = path.strip("/").split("/")
    if path_parts and _is_uuid(path_parts[-1]):
        station_id = path_parts[-1]
        if station_id not in station_data:
            station_data[station_id] = {}
        station_data[station_id].update(data)


# ---------------------------------------------------------------------------
# Record parser
# ---------------------------------------------------------------------------

def _parse_record(
    record: dict[str, Any], now: datetime
) -> tuple[Station | None, PriceSnapshot | None]:
    """Map a raw Clever Firebase location record to a Station + PriceSnapshot pair.

    Field names are tried in order of likelihood based on Clever's known schema.
    On first runs, check DEBUG logs to confirm actual field names and tighten this.
    """
    # --- Location ID (required) ---
    location_id_raw = (
        record.get("locationId")
        or record.get("id")
        or record.get("stationId")
    )
    if not location_id_raw:
        logger.debug("No location ID in record, skipping. Keys: %s", list(record.keys()))
        return None, None

    station_id = (
        uuid.UUID(str(location_id_raw))
        if _is_uuid(str(location_id_raw))
        else uuid.uuid5(uuid.NAMESPACE_URL, f"clever:{location_id_raw}")
    )

    # --- Coordinates (required) ---
    lat = record.get("lat") or record.get("latitude")
    lon = record.get("lng") or record.get("lon") or record.get("longitude")

    if lat is None or lon is None:
        # Fall back to geohash decoding
        geohash = record.get("geohash")
        if geohash:
            lat, lon = _geohash_to_latlon(geohash)
        else:
            logger.debug(
                "No coordinates for %s, skipping. Keys: %s",
                location_id_raw,
                list(record.keys()),
            )
            return None, None

    # --- Price (required for snapshot) ---
    price_kwh = (
        record.get("pricePerKwh")
        or record.get("price_kwh")
        or record.get("kwhPrice")
        or record.get("unitPrice")
        or record.get("pris")
    )
    if price_kwh is None:
        logger.debug(
            "No price for station %s, skipping snapshot. Keys: %s",
            location_id_raw,
            list(record.keys()),
        )
        return None, None

    station = Station(
        id=station_id,
        operator_id=_OPERATOR_ID,
        external_id=str(location_id_raw),
        name=record.get("name") or record.get("title") or str(location_id_raw),
        address=record.get("address") or record.get("street"),
        lat=float(lat),
        lon=float(lon),
        connector_types=record.get("connectorTypes") or record.get("connectors") or [],
        updated_at=now,
    )

    snapshot = PriceSnapshot(
        time=now,
        station_id=station_id,
        operator_id=_OPERATOR_ID,
        price_kwh=price_kwh,
        price_min=record.get("pricePerMinute") or record.get("price_min"),
        session_fee=record.get("sessionFee") or record.get("session_fee"),
        currency=record.get("currency", "DKK"),
        source_raw=record,
    )

    return station, snapshot


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError):
        return False


def _geohash_to_latlon(geohash: str) -> tuple[float, float]:
    """Decode a geohash string to (lat, lon) centre point."""
    _BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
    lat_range = (-90.0, 90.0)
    lon_range = (-180.0, 180.0)
    is_lon = True

    for char in geohash.lower():
        char_idx = _BASE32.index(char)
        for shift in range(4, -1, -1):
            bit = (char_idx >> shift) & 1
            if is_lon:
                mid = (lon_range[0] + lon_range[1]) / 2
                lon_range = (mid, lon_range[1]) if bit else (lon_range[0], mid)
            else:
                mid = (lat_range[0] + lat_range[1]) / 2
                lat_range = (mid, lat_range[1]) if bit else (lat_range[0], mid)
            is_lon = not is_lon

    return (lat_range[0] + lat_range[1]) / 2, (lon_range[0] + lon_range[1]) / 2


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    from db.session import init_engine
    await init_engine()

    crawler = CleverCrawler()
    await crawler.run()


if __name__ == "__main__":
    asyncio.run(main())
