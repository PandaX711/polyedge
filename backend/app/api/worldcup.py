import json
import logging
from dataclasses import dataclass

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

GAMMA_URL = settings.polymarket_gamma_url


class OutcomeOut(BaseModel):
    team: str
    yes_price: float
    no_price: float
    condition_id: str
    volume: float
    liquidity: float


class MultiOutcomeEventOut(BaseModel):
    event_id: str
    title: str
    slug: str
    total_volume: float
    total_liquidity: float
    outcomes: list[OutcomeOut]


@router.get("/winner", response_model=MultiOutcomeEventOut | None)
async def get_wc_winner_market():
    """Fetch the 2026 FIFA World Cup Winner multi-outcome market."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # First find the event via a sample market
        resp = await client.get(
            f"{GAMMA_URL}/markets",
            params={
                "tag": "world-cup",
                "active": "true",
                "closed": "false",
                "limit": 100,
            },
        )
        resp.raise_for_status()
        markets = resp.json()

        # Find a "win the 2026 FIFA World Cup" market to get event ID
        event_id = None
        for m in markets:
            if "win the 2026 FIFA World Cup" in m.get("question", ""):
                events = m.get("events", [])
                if events:
                    event_id = events[0].get("id")
                    break

        if not event_id:
            return None

        # Fetch the full event with all markets
        resp2 = await client.get(f"{GAMMA_URL}/events/{event_id}")
        if resp2.status_code != 200:
            logger.error("Failed to fetch event %s: %s", event_id, resp2.status_code)
            return None

        event = resp2.json()
        event_markets = event.get("markets", [])

        outcomes = []
        total_vol = 0.0
        total_liq = 0.0

        for em in event_markets:
            question = em.get("question", "")
            if "win the 2026 FIFA World Cup" not in question:
                continue

            team = em.get("groupItemTitle", "")
            if not team:
                team = question.replace("Will ", "").replace(" win the 2026 FIFA World Cup?", "")

            outcome_prices = em.get("outcomePrices", "")
            try:
                prices = json.loads(outcome_prices) if isinstance(outcome_prices, str) else outcome_prices
                yes_price = float(prices[0]) if prices else 0.0
                no_price = float(prices[1]) if len(prices) > 1 else 1.0 - yes_price
            except (json.JSONDecodeError, IndexError, ValueError):
                yes_price = 0.0
                no_price = 1.0

            vol = float(em.get("volume", 0) or 0)
            liq = float(em.get("liquidity", 0) or 0)
            total_vol += vol
            total_liq += liq

            outcomes.append(OutcomeOut(
                team=team,
                yes_price=yes_price,
                no_price=no_price,
                condition_id=em.get("conditionId", ""),
                volume=vol,
                liquidity=liq,
            ))

        # Sort by probability descending
        outcomes.sort(key=lambda o: o.yes_price, reverse=True)

        return MultiOutcomeEventOut(
            event_id=str(event_id),
            title=event.get("title", "2026 FIFA World Cup Winner"),
            slug=event.get("slug", ""),
            total_volume=total_vol,
            total_liquidity=total_liq,
            outcomes=outcomes,
        )


@router.get("/qualifiers", response_model=list[OutcomeOut])
async def get_wc_qualifiers():
    """Fetch World Cup qualifier markets."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{GAMMA_URL}/markets",
            params={
                "tag": "world-cup",
                "active": "true",
                "closed": "false",
                "limit": 200,
            },
        )
        resp.raise_for_status()
        markets = resp.json()

        outcomes = []
        for m in markets:
            question = m.get("question", "")
            if "qualify for the 2026 FIFA World Cup" not in question:
                continue

            team = m.get("groupItemTitle", "")
            if not team:
                team = question.replace("Will ", "").replace(" qualify for the 2026 FIFA World Cup?", "")

            outcome_prices = m.get("outcomePrices", "")
            try:
                prices = json.loads(outcome_prices) if isinstance(outcome_prices, str) else outcome_prices
                yes_price = float(prices[0]) if prices else 0.0
                no_price = float(prices[1]) if len(prices) > 1 else 1.0 - yes_price
            except (json.JSONDecodeError, IndexError, ValueError):
                yes_price = 0.0
                no_price = 1.0

            outcomes.append(OutcomeOut(
                team=team,
                yes_price=yes_price,
                no_price=no_price,
                condition_id=m.get("conditionId", ""),
                volume=float(m.get("volume", 0) or 0),
                liquidity=float(m.get("liquidity", 0) or 0),
            ))

        outcomes.sort(key=lambda o: o.yes_price, reverse=True)
        return outcomes
