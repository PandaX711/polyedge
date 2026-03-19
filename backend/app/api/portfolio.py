from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.market import Position, Signal

router = APIRouter()


class PositionOut(BaseModel):
    id: int
    condition_id: str
    side: str
    size: float
    entry_price: float
    current_price: Optional[float] = None
    pnl: float = 0.0
    status: str = "open"
    signal_id: Optional[int] = None
    opened_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PortfolioSummary(BaseModel):
    total_positions: int
    open_positions: int
    total_invested: float
    total_pnl: float
    pending_signals: int


@router.get("/positions", response_model=list[PositionOut])
async def list_positions(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Position).order_by(Position.opened_at.desc())
    if status:
        stmt = stmt.where(Position.status == status)
    result = await db.execute(stmt)
    return [PositionOut.model_validate(p) for p in result.scalars().all()]


@router.get("/summary", response_model=PortfolioSummary)
async def portfolio_summary(db: AsyncSession = Depends(get_db)):
    # Total positions
    total_result = await db.execute(select(func.count(Position.id)))
    total = total_result.scalar() or 0

    # Open positions
    open_result = await db.execute(
        select(func.count(Position.id)).where(Position.status == "open")
    )
    open_count = open_result.scalar() or 0

    # Total invested (open positions)
    invested_result = await db.execute(
        select(func.coalesce(func.sum(Position.size), 0)).where(
            Position.status == "open"
        )
    )
    total_invested = invested_result.scalar() or 0.0

    # Total PnL
    pnl_result = await db.execute(
        select(func.coalesce(func.sum(Position.pnl), 0))
    )
    total_pnl = pnl_result.scalar() or 0.0

    # Pending signals
    pending_result = await db.execute(
        select(func.count(Signal.id)).where(Signal.status == "pending")
    )
    pending = pending_result.scalar() or 0

    return PortfolioSummary(
        total_positions=total,
        open_positions=open_count,
        total_invested=float(total_invested),
        total_pnl=float(total_pnl),
        pending_signals=pending,
    )
