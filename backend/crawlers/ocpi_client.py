from __future__ import annotations

from types import TracebackType

import httpx


class OCPIClient:
    """Reusable async OCPI 2.2 HTTP client.

    Callers are responsible for calling close() or using the async context
    manager to release the underlying connection pool.
    """

    def __init__(self, base_url: str, token: str) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Token {token}"},
            timeout=30.0,
        )

    async def get_locations(self) -> list[dict]:
        """Fetch all OCPI Location objects, following pagination via Link header."""
        locations: list[dict] = []
        url = "/ocpi/cpo/2.2/locations"

        while url:
            response = await self._client.get(url)
            response.raise_for_status()
            body = response.json()
            locations.extend(body.get("data", []))
            # OCPI uses Link: <url>; rel="next" for pagination
            link = response.headers.get("Link", "")
            url = _parse_next_link(link)

        return locations

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> OCPIClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()


def _parse_next_link(link_header: str) -> str | None:
    """Extract the 'next' URL from an HTTP Link header, or return None."""
    for part in link_header.split(","):
        segments = [s.strip() for s in part.split(";")]
        if len(segments) == 2 and segments[1] == 'rel="next"':
            return segments[0].strip("<>")
    return None
