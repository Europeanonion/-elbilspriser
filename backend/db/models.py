from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    Text,
    Float,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Station(Base):
    __tablename__ = "stations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    operator_id: Mapped[int] = mapped_column(SmallInteger, nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    # List of connector type strings, e.g. ["CCS2", "CHAdeMO"]
    connector_types: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class PriceSnapshot(Base):
    """TimescaleDB hypertable — partitioned on `time`.

    After running the Alembic migration you must execute:
        SELECT create_hypertable('price_snapshots', 'time', if_not_exists => TRUE);
    This is handled automatically by the 001_initial migration's upgrade().
    """

    __tablename__ = "price_snapshots"

    time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, nullable=False
    )
    station_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stations.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    operator_id: Mapped[int] = mapped_column(SmallInteger, nullable=False, index=True)
    price_kwh: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    price_min: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    session_fee: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    # ISO 4217 three-letter currency code
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="DKK")
    source_raw: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
