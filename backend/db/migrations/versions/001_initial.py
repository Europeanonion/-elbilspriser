"""Initial schema: stations and price_snapshots

Revision ID: 001
Revises:
Create Date: 2025-05-13

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "stations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("operator_id", sa.SmallInteger(), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lon", sa.Float(), nullable=False),
        sa.Column(
            "connector_types",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
    )

    # Plain btree index on (operator_id) for per-operator queries.
    op.create_index("ix_stations_operator_id", "stations", ["operator_id"])

    # Btree index on (lat, lon) for bounding-box pre-filter.
    # Replace with a PostGIS geography index for proper great-circle distance:
    #   CREATE INDEX ix_stations_geography
    #     ON stations USING GIST (ST_MakePoint(lon, lat)::geography);
    op.create_index("ix_stations_lat_lon", "stations", ["lat", "lon"])

    op.create_table(
        "price_snapshots",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False, primary_key=True),
        sa.Column(
            "station_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("stations.id", ondelete="CASCADE"),
            nullable=False,
            primary_key=True,
        ),
        sa.Column("operator_id", sa.SmallInteger(), nullable=False),
        sa.Column("price_kwh", sa.Numeric(6, 4), nullable=False),
        sa.Column("price_min", sa.Numeric(6, 4), nullable=True),
        sa.Column("session_fee", sa.Numeric(6, 2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="DKK"),
        sa.Column(
            "source_raw",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
    )

    op.create_index(
        "ix_price_snapshots_operator_id", "price_snapshots", ["operator_id"]
    )

    # TimescaleDB: convert price_snapshots to a hypertable partitioned by time.
    # The table must exist before this call; TimescaleDB replaces the primary key
    # with a composite (time, station_id) constraint automatically.
    op.execute(
        "SELECT create_hypertable('price_snapshots', 'time', if_not_exists => TRUE)"
    )

    # Compression policy omitted — requires TimescaleDB Community Edition.
    # To enable on Community: ALTER TABLE price_snapshots SET (timescaledb.compress = true);
    #                         SELECT add_compression_policy('price_snapshots', INTERVAL '7 days');


def downgrade() -> None:
    op.drop_table("price_snapshots")
    op.drop_table("stations")
