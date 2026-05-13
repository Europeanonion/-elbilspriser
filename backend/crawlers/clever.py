"""Clever charging station crawler — public REST API on clever.dk.

Clever's map loads data from two unauthenticated REST endpoints:

  GET /api/v2/chargers/locations          — bulk dict of all station UUIDs
  GET /api/v2/chargers/location/{uuid}    — per-station detail with pricing

Pricing products in the detail response:
  GO   — pay-as-you-go, no subscription needed, highest kWh rate
  MOVE — mid-tier monthly subscription, lower rate
  LINK — B2B/fleet subscription
  BOX  — home charger + public network bundle
  KEY  — B2B key-access (ex. VAT)
  SPOT — real-time electricity spot price + margin, hourly updates

We store the GO-product price at the crawl time as the canonical price_kwh,
since GO is the baseline any consumer pays without a subscription.
"""
from __future__ import annotations

import asyncio
import logging
import re
import uuid as uuid_mod
import zoneinfo
from datetime import datetime, timezone
from typing import Any

import httpx

from crawlers.base import BaseCrawler
from db.models import PriceSnapshot, Station

logger = logging.getLogger(__name__)

_LOCATIONS_URL = "https://clever.dk/api/v2/chargers/locations"
_DETAIL_URL = "https://clever.dk/api/v2/chargers/location/{uuid}"
_HEADERS = {
    "Referer": "https://clever.dk/ladekort/",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}
_OPERATOR_ID = 1
_CONCURRENCY = 15
_DK_TZ = zoneinfo.ZoneInfo("Europe/Copenhagen")
_PREFERRED_PRODUCT = "GO"


class CleverCrawler(BaseCrawler):
    name = "clever"

    async def fetch(self) -> list[dict]:
        async with httpx.AsyncClient(headers=_HEADERS, timeout=30.0) as client:
            # Step 1: bulk list to get all location IDs
            resp = await client.get(_LOCATIONS_URL)
            resp.raise_for_status()
            bulk: dict[str, dict] = resp.json()

            # Skip roaming-partner locations (other CPOs showing in Clever's app)
            native_ids = [k for k, v in bulk.items() if not v.get("isRoamingPartner")]
            logger.info("Clever: %d native locations (skipped %d roaming partners)", len(native_ids), len(bulk) - len(native_ids))

            # Step 2: concurrent per-station detail fetches (includes pricing)
            sem = asyncio.Semaphore(_CONCURRENCY)
            errors = 0

            async def _fetch_one(loc_id: str) -> dict | None:
                async with sem:
                    try:
                        r = await client.get(_DETAIL_URL.format(uuid=loc_id))
                        r.raise_for_status()
                        return r.json()
                    except Exception as exc:
                        logger.debug("Detail fetch failed for %s: %s", loc_id, exc)
                        return None

            raw_results: list[dict | None] = await asyncio.gather(
                *[_fetch_one(loc_id) for loc_id in native_ids]
            )

        results = []
        for r in raw_results:
            if r is None:
                errors += 1
            else:
                results.append(r)

        logger.info(
            "Clever: fetched %d/%d station details (%d errors)",
            len(results),
            len(native_ids),
            errors,
        )
        return results

    async def parse(self, raw: list[dict]) -> tuple[list[Station], list[PriceSnapshot]]:
        now = datetime.now(timezone.utc)
        stations: list[Station] = []
        snapshots: list[PriceSnapshot] = []

        for record in raw:
            try:
                station, snapshot = _parse_record(record, now)
                if station is not None:
                    stations.append(station)
                if snapshot is not None:
                    snapshots.append(snapshot)
            except Exception as exc:
                logger.warning(
                    "Skipping record %s: %s", record.get("locationId", "?"), exc
                )

        logger.info(
            "Clever: parsed %d stations, %d snapshots from %d records",
            len(stations),
            len(snapshots),
            len(raw),
        )
        return stations, snapshots


def _parse_record(
    record: dict[str, Any], now: datetime
) -> tuple[Station | None, PriceSnapshot | None]:
    location_id_str = record.get("locationId")
    if not location_id_str:
        return None, None

    try:
        station_id = uuid_mod.UUID(location_id_str)
    except ValueError:
        station_id = uuid_mod.uuid5(uuid_mod.NAMESPACE_URL, f"clever:{location_id_str}")

    coords = record.get("coordinates", {})
    lat = coords.get("lat")
    lon = coords.get("lng")
    if lat is None or lon is None:
        logger.debug("No coordinates for %s, skipping", location_id_str)
        return None, None

    addr_obj = record.get("address") or {}
    address = ", ".join(
        p for p in [addr_obj.get("address"), addr_obj.get("postalCode"), addr_obj.get("city")]
        if p
    ) or None

    connector_types: list[str] = []
    for plug in record.get("plugs", []):
        for conn in plug.get("connectors", []):
            pt = conn.get("plugType")
            if pt and pt not in connector_types:
                connector_types.append(pt)

    station = Station(
        id=station_id,
        operator_id=_OPERATOR_ID,
        external_id=location_id_str,
        name=record.get("name") or location_id_str,
        address=address,
        lat=float(lat),
        lon=float(lon),
        connector_types=connector_types,
        updated_at=now,
    )

    price_kwh = _extract_current_price(record, now)
    snapshot = (
        PriceSnapshot(
            time=now,
            station_id=station_id,
            operator_id=_OPERATOR_ID,
            price_kwh=price_kwh,
            price_min=None,
            session_fee=None,
            currency="DKK",
            source_raw=record,
        )
        if price_kwh is not None
        else None
    )

    return station, snapshot


def _extract_current_price(record: dict[str, Any], now: datetime) -> float | None:
    """Return GO-product kWh price at the crawl time, or None if unavailable."""
    plugs = record.get("plugs", [])
    if not plugs:
        return None

    prices_list = plugs[0].get("prices", [])
    by_product = {p["product"]: p for p in prices_list if "product" in p}

    product = by_product.get(_PREFERRED_PRODUCT) or next(iter(by_product.values()), None)
    if product is None:
        return None

    return _find_price_at(product.get("timeTable", []), now)


def _find_price_at(timetable: list[dict], now: datetime) -> float | None:
    if not timetable:
        return None

    now_dk = now.astimezone(_DK_TZ)
    today_str = now_dk.strftime("%d.%m.%Y")
    now_time_str = now_dk.strftime("%H:%M")

    # Find the entry whose window contains the current moment
    for entry in timetable:
        from_date = entry.get("from_date_string", "")
        from_time = entry.get("from_time_string", "")
        to_time = entry.get("to_time_string", "99:99")
        if from_date == today_str and from_time <= now_time_str < to_time:
            return _parse_price_string(entry.get("price_string", ""))

    # Fallback: first entry's price
    return _parse_price_string(timetable[0].get("price_string", ""))


def _parse_price_string(price_str: str) -> float | None:
    """Parse Danish price string '4,09 kr.' → 4.09."""
    if not price_str:
        return None
    cleaned = re.sub(r"[^\d,.]", "", price_str).replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


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
