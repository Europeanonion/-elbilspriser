"""Spirii OCPI crawler.

TODO: Implement _parse_location() to map Spirii OCPI Location objects to
      Station + PriceSnapshot rows once the response schema is confirmed.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone

from crawlers.base import BaseCrawler
from crawlers.ocpi_client import OCPIClient
from db.models import PriceSnapshot

logger = logging.getLogger(__name__)

_OPERATOR_ID = 2  # internal ID assigned to Spirii


class SpiriiCrawler(BaseCrawler):
    name = "spirii"

    async def fetch(self) -> list[dict]:
        base_url = os.environ["SPIRII_BASE_URL"]
        token = os.environ["SPIRII_API_KEY"]
        async with OCPIClient(base_url=base_url, token=token) as client:
            locations = await client.get_locations()
        logger.info("Spirii: fetched %d locations", len(locations))
        return locations

    async def parse(self, raw: list[dict]) -> list[PriceSnapshot]:
        # TODO: parse OCPI Location objects into PriceSnapshot rows.
        logger.warning("Spirii parse() not yet implemented — returning empty list")
        return []


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    crawler = SpiriiCrawler()
    await crawler.run()


if __name__ == "__main__":
    asyncio.run(main())
