from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.market import Market, Price

router = APIRouter()


class MarketOut(BaseModel):
    id: int
    condition_id: str
    question: str
    slug: Optional[str] = None
    league: Optional[str] = None
    home_team: Optional[str] = None
    away_team: Optional[str] = None
    match_date: Optional[datetime] = None
    active: int = 1
    volume: float = 0.0
    liquidity: float = 0.0
    yes_price: Optional[float] = None  # Latest price
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PriceOut(BaseModel):
    yes_price: float
    no_price: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    spread: Optional[float] = None
    volume_1h: Optional[float] = None
    timestamp: Optional[datetime] = None

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[MarketOut])
async def list_markets(
    league: Optional[str] = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Market)
    if active_only:
        stmt = stmt.where(Market.active == 1)
    if league:
        stmt = stmt.where(Market.league == league)
    stmt = stmt.order_by(Market.volume.desc())
    result = await db.execute(stmt)
    markets = result.scalars().all()

    # Batch-fetch latest prices for all markets
    cids = [m.condition_id for m in markets]
    price_map: dict[str, float] = {}
    if cids:
        from sqlalchemy import func as sqlfunc
        # Get latest price per condition_id via subquery
        sub = (
            select(Price.condition_id, sqlfunc.max(Price.id).label("max_id"))
            .where(Price.condition_id.in_(cids))
            .group_by(Price.condition_id)
            .subquery()
        )
        price_stmt = select(Price).join(sub, Price.id == sub.c.max_id)
        price_result = await db.execute(price_stmt)
        for p in price_result.scalars().all():
            price_map[p.condition_id] = p.yes_price

    out = []
    for m in markets:
        market_dict = {
            "id": m.id,
            "condition_id": m.condition_id,
            "question": m.question,
            "slug": m.slug,
            "league": m.league,
            "home_team": m.home_team,
            "away_team": m.away_team,
            "match_date": m.match_date,
            "active": m.active,
            "volume": m.volume,
            "liquidity": m.liquidity,
            "yes_price": price_map.get(m.condition_id),
            "created_at": m.created_at,
        }
        out.append(MarketOut(**market_dict))
    return out


@router.get("/{condition_id}")
async def get_market(condition_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Market).where(Market.condition_id == condition_id)
    result = await db.execute(stmt)
    market = result.scalar_one_or_none()
    if not market:
        return {"error": "Market not found"}
    return MarketOut.model_validate(market)


@router.get("/{condition_id}/prices", response_model=list[PriceOut])
async def get_prices(
    condition_id: str,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Price)
        .where(Price.condition_id == condition_id)
        .order_by(Price.timestamp.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return [PriceOut.model_validate(p) for p in result.scalars().all()]
