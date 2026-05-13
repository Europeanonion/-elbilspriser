from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import text

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
        (:operator_id::smallint IS NULL OR ps.operator_id = :operator_id::smallint)
        AND s.lat BETWEEN :lat_min AND :lat_max
        AND s.lon BETWEEN :lon_min AND :lon_max
    ORDER BY ps.station_id, ps.time DESC
    """
)

_KM_PER_DEGREE_LAT = 111.0


def _degree_delta(radius_km: float, lat: float) -> tuple[float, float]:
    import math

    lat_delta = radius_km / _KM_PER_DEGREE_LAT
    lon_delta = radius_km / (_KM_PER_DEGREE_LAT * math.cos(math.radians(lat)))
    return lat_delta, lon_delta


@router.get("/prices")
async def list_prices(
    db: DBSession,
    lat: float = Query(..., description="Centre latitude"),
    lon: float = Query(..., description="Centre longitude"),
    radius_km: float = Query(25.0, gt=0, le=200),
    operator_id: int | None = Query(None),
) -> list[dict[str, Any]]:
    lat_delta, lon_delta = _degree_delta(radius_km, lat)

    rows = await db.execute(
        _LATEST_PRICES_SQL,
        {
            "operator_id": operator_id,
            "lat_min": lat - lat_delta,
            "lat_max": lat + lat_delta,
            "lon_min": lon - lon_delta,
            "lon_max": lon + lon_delta,
        },
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
