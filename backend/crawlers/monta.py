"""Monta Partner API crawler.

TODO: Monta uses its own Partner API rather than plain OCPI.
      Update the base_url path and auth scheme once confirmed.
      Implement _parse_location() to map Monta charge point objects to
      Station + PriceSnapshot rows.
"""
from __future__ import annotations

import asyncio
import logging
import os

from crawlers.base import BaseCrawler
from crawlers.ocpi_client import OCPIClient
from db.models import PriceSnapshot, Station

logger = logging.getLogger(__name__)

_OPERATOR_ID = 3  # internal ID assigned to Monta


class MontaCrawler(BaseCrawler):
    name = "monta"

    async def fetch(self) -> list[dict]:
        base_url = os.environ["MONTA_BASE_URL"]
        token = os.environ["MONTA_API_KEY"]
        # Monta Partner API mirrors OCPI locations at this path.
        async with OCPIClient(base_url=base_url, token=token) as client:
            locations = await client.get_locations()
        logger.info("Monta: fetched %d locations", len(locations))
        return locations

    async def parse(self, raw: list[dict]) -> tuple[list[Station], list[PriceSnapshot]]:
        # TODO: parse Monta charge point objects into Station + PriceSnapshot rows.
        logger.warning("Monta parse() not yet implemented — returning empty")
        return [], []


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    from db.session import init_engine
    await init_engine()
    crawler = MontaCrawler()
    await crawler.run()


if __name__ == "__main__":
    asyncio.run(main())
