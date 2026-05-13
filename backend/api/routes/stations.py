from __future__ import annotations

import logging
import math
from typing import Any

from fastapi import APIRouter, Query
from sqlalchemy import text

from api.deps import DBSession

logger = logging.getLogger(__name__)

router = APIRouter(tags=["stations"])

_OPERATOR_NAMES: dict[int, str] = {1: "Clever"}

_STATIONS_WITH_PRICE_SQL = text(
    """
    SELECT
        s.id,
        s.name,
        s.address,
        s.lat,
        s.lon,
        s.operator_id,
        s.connector_types,
        s.updated_at,
        ps.price_kwh,
        ps.price_min,
        ps.session_fee,
        ps.currency,
        ps.time AS price_updated_at
    FROM stations s
    LEFT JOIN LATERAL (
        SELECT price_kwh, price_min, session_fee, currency, time
        FROM price_snapshots
        WHERE station_id = s.id
        ORDER BY time DESC
        LIMIT 1
    ) ps ON true
    WHERE
        s.lat BETWEEN :lat_min AND :lat_max
        AND s.lon BETWEEN :lon_min AND :lon_max
    ORDER BY s.name
    """
)

_KM_PER_DEGREE_LAT = 111.0


def _degree_delta(radius_km: float, lat: float) -> tuple[float, float]:
    lat_delta = radius_km / _KM_PER_DEGREE_LAT
    lon_delta = radius_km / (_KM_PER_DEGREE_LAT * math.cos(math.radians(lat)))
    return lat_delta, lon_delta


@router.get("/stations")
async def list_stations(
    db: DBSession,
    lat: float = Query(..., description="Centre latitude"),
    lon: float = Query(..., description="Centre longitude"),
    radius_km: float = Query(25.0, gt=0, le=200),
) -> list[dict[str, Any]]:
    lat_delta, lon_delta = _degree_delta(radius_km, lat)

    rows = await db.execute(
        _STATIONS_WITH_PRICE_SQL,
        {
            "lat_min": lat - lat_delta,
            "lat_max": lat + lat_delta,
            "lon_min": lon - lon_delta,
            "lon_max": lon + lon_delta,
        },
    )

    return [
        {
            "id": str(row.id),
            "name": row.name,
            "address": row.address,
            "lat": row.lat,
            "lon": row.lon,
            "operator": _OPERATOR_NAMES.get(row.operator_id, str(row.operator_id)),
            "connector_types": row.connector_types,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            "price": {
                "price_kwh": float(row.price_kwh) if row.price_kwh is not None else None,
                "price_min": float(row.price_min) if row.price_min is not None else None,
                "session_fee": float(row.session_fee) if row.session_fee is not None else None,
                "currency": row.currency,
                "updated_at": row.price_updated_at.isoformat() if row.price_updated_at else None,
            },
        }
        for row in rows
    ]
