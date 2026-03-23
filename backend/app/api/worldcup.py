import json
import logging

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.market import VolumeSnapshot

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


class WCAnalysisOut(BaseModel):
    most_undervalued: list[dict] = []
    most_overvalued: list[dict] = []
    dark_horses: list[dict] = []
    top_recommendation: dict = {}
    market_overview: str = ""


@router.post("/analyze", response_model=WCAnalysisOut | None)
async def analyze_wc_winner():
    """Run AI analysis on the World Cup winner market."""
    from app.ai.analyst import MatchAnalyst
    from app.config import settings as cfg

    if not cfg.anthropic_api_key:
        return None

    # Get current winner data
    winner = await get_wc_winner_market()
    if not winner or not winner.outcomes:
        return None

    analyst = MatchAnalyst()
    outcomes_dicts = [
        {"team": o.team, "yes_price": o.yes_price, "volume": o.volume}
        for o in winner.outcomes
    ]

    result = await analyst.analyze_wc_winner(
        outcomes=outcomes_dicts,
        total_volume=winner.total_volume,
        total_liquidity=winner.total_liquidity,
    )

    if not result:
        return None

    return WCAnalysisOut(
        most_undervalued=result.most_undervalued,
        most_overvalued=result.most_overvalued,
        dark_horses=result.dark_horses,
        top_recommendation=result.top_recommendation,
        market_overview=result.market_overview,
    )


class VolumeTrendPoint(BaseModel):
    date: str
    volume: float
    liquidity: float
    market_count: int


@router.get("/volume-trend", response_model=list[VolumeTrendPoint])
async def get_volume_trend(
    category: str = "worldcup_total",
    db: AsyncSession = Depends(get_db),
):
    """Get historical volume trend data for charting."""
    stmt = (
        select(VolumeSnapshot)
        .where(VolumeSnapshot.category == category)
        .order_by(VolumeSnapshot.date.asc())
    )
    result = await db.execute(stmt)
    snapshots = result.scalars().all()

    return [
        VolumeTrendPoint(
            date=s.date,
            volume=s.total_volume,
            liquidity=s.total_liquidity,
            market_count=s.market_count,
        )
        for s in snapshots
    ]
