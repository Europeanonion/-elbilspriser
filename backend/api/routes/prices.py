from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import SmallInteger, bindparam, text

from api.deps import DBSession

logger = logging.getLogger(__name__)

router = APIRouter(tags=["prices"])

_OPERATOR_NAMES: dict[int, str] = {1: "Clever"}

# Haversine-based bounding box pre-filter keeps the query fast without PostGIS.
# The radius_km constraint is applied approximately via degree conversion;
# a proper great-circle filter should be added once PostGIS is confirmed available.
_LATEST_PRICES_SQL = text(
    """
    SELECT DISTINCT ON (ps.station_id)
        ps.station_id,
        s.name,
        ps.operator_id,
        ps.price_kwh,
        ps.price_min,
        ps.session_fee,
        ps.currency,
        ps.time AS updated_at
    FROM price_snapshots ps
    JOIN stations s ON s.id = ps.station_id
    WHERE
        (:operator_id IS NULL OR ps.operator_id = :operator_id)
        AND s.lat BETWEEN :lat_min AND :lat_max
        AND s.lon BETWEEN :lon_min AND :lon_max
    ORDER BY ps.station_id, ps.time DESC
    """
).bindparams(bindparam("operator_id", type_=SmallInteger()))

_KM_PER_DEGREE_LAT = 111.0

# Geographic bounding box covering all of Denmark (mainland + Bornholm).
# Used as the default when no lat/lon/radius_km is supplied.
_DK_BBOX = {"lat_min": 54.5, "lat_max": 57.8, "lon_min": 7.9, "lon_max": 15.2}


def _bbox_from_radius(radius_km: float, lat: float, lon: float) -> dict[str, float]:
    import math
    lat_delta = radius_km / _KM_PER_DEGREE_LAT
    lon_delta = radius_km / (_KM_PER_DEGREE_LAT * math.cos(math.radians(lat)))
    return {
        "lat_min": lat - lat_delta,
        "lat_max": lat + lat_delta,
        "lon_min": lon - lon_delta,
        "lon_max": lon + lon_delta,
    }


_OPERATOR_PRICE_SQL = text(
    """
    SELECT
        AVG(price_kwh)  AS price_kwh,
        MAX(time)       AS updated_at,
        COUNT(*)        AS station_count
    FROM (
        SELECT DISTINCT ON (station_id)
            price_kwh, time
        FROM price_snapshots
        WHERE operator_id = :operator_id
        ORDER BY station_id, time DESC
    ) latest
    """
).bindparams(bindparam("operator_id", type_=SmallInteger()))


@router.get("/operator-price")
async def operator_price(
    db: DBSession,
    operator_id: int = Query(1),
) -> dict[str, Any]:
    row = (await db.execute(_OPERATOR_PRICE_SQL, {"operator_id": operator_id})).one_or_none()
    if row is None or row.price_kwh is None:
        raise HTTPException(status_code=404, detail="No price data for operator")
    return {
        "operator_id": operator_id,
        "operator": _OPERATOR_NAMES.get(operator_id, str(operator_id)),
        "price_kwh": float(row.price_kwh),
        "updated_at": row.updated_at.isoformat(),
        "station_count": row.station_count,
    }


@router.get("/prices")
async def list_prices(
    db: DBSession,
    lat: float | None = Query(None, description="Centre latitude — omit for all of Denmark"),
    lon: float | None = Query(None, description="Centre longitude — omit for all of Denmark"),
    radius_km: float | None = Query(None, gt=0, le=500),
    operator_id: int | None = Query(None),
) -> list[dict[str, Any]]:
    if lat is not None and lon is not None and radius_km is not None:
        bbox = _bbox_from_radius(radius_km, lat, lon)
    else:
        bbox = _DK_BBOX

    rows = await db.execute(
        _LATEST_PRICES_SQL,
        {"operator_id": operator_id, **bbox},
    )

    return [
        {
            "id": str(row.station_id),
            "name": row.name,
            "operator": _OPERATOR_NAMES.get(row.operator_id, str(row.operator_id)),
            "price_kwh": float(row.price_kwh) if row.price_kwh is not None else None,
            "price_min": float(row.price_min) if row.price_min is not None else None,
            "session_fee": float(row.session_fee) if row.session_fee is not None else None,
            "currency": row.currency,
            "updated_at": row.updated_at.isoformat(),
        }
        for row in rows
    ]
