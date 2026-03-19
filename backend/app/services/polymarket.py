import logging
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

FOOTBALL_TAGS = ["soccer", "football", "epl", "laliga", "seriea", "bundesliga", "ligue1", "ucl", "world-cup"]


class GammaClient:
    """Client for Polymarket Gamma API (market discovery)."""

    def __init__(self):
        self.base_url = settings.polymarket_gamma_url
        self.client = httpx.AsyncClient(timeout=30.0)

    async def get_football_markets(self, limit: int = 100, offset: int = 0) -> list[dict]:
        """Fetch active football/soccer markets."""
        markets = []
        for tag in FOOTBALL_TAGS:
            try:
                resp = await self.client.get(
                    f"{self.base_url}/markets",
                    params={
                        "tag": tag,
                        "active": True,
                        "closed": False,
                        "limit": limit,
                        "offset": offset,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                if isinstance(data, list):
                    markets.extend(data)
            except httpx.HTTPError as e:
                logger.error("Gamma API error for tag %s: %s", tag, e)
        # Deduplicate by condition_id
        seen = set()
        unique = []
        for m in markets:
            cid = m.get("conditionId") or m.get("condition_id")
            if cid and cid not in seen:
                seen.add(cid)
                unique.append(m)
        return unique

    async def get_market(self, condition_id: str) -> Optional[dict]:
        """Fetch a single market by condition ID."""
        try:
            resp = await self.client.get(
                f"{self.base_url}/markets",
                params={"condition_id": condition_id},
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list) and data:
                return data[0]
            return data if isinstance(data, dict) else None
        except httpx.HTTPError as e:
            logger.error("Gamma API error for %s: %s", condition_id[:16], e)
            return None

    async def get_events(self, slug: str) -> Optional[dict]:
        """Fetch event by slug."""
        try:
            resp = await self.client.get(
                f"{self.base_url}/events",
                params={"slug": slug},
            )
            resp.raise_for_status()
            data = resp.json()
            return data[0] if data else None
        except httpx.HTTPError as e:
            logger.error("Gamma API error: %s", e)
            return None

    async def close(self):
        await self.client.aclose()
