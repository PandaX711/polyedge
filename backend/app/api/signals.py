from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.market import Signal

router = APIRouter()


class SignalOut(BaseModel):
    id: int
    condition_id: str
    strategy: str
    direction: str
    confidence: float
    suggested_size: Optional[float] = None
    poly_prob: Optional[float] = None
    book_prob: Optional[float] = None
    ai_prob: Optional[float] = None
    consensus_delta: Optional[float] = None
    status: str = "pending"
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SignalAction(BaseModel):
    action: str  # "confirm" or "reject"


@router.get("/", response_model=list[SignalOut])
async def list_signals(
    status: Optional[str] = None,
    strategy: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Signal).order_by(Signal.created_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(Signal.status == status)
    if strategy:
        stmt = stmt.where(Signal.strategy == strategy)
    result = await db.execute(stmt)
    return [SignalOut.model_validate(s) for s in result.scalars().all()]


@router.post("/{signal_id}/action")
async def action_signal(
    signal_id: int,
    body: SignalAction,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Signal).where(Signal.id == signal_id)
    result = await db.execute(stmt)
    signal = result.scalar_one_or_none()
    if not signal:
        return {"error": "Signal not found"}

    if body.action == "confirm":
        signal.status = "confirmed"
    elif body.action == "reject":
        signal.status = "expired"
    else:
        return {"error": "Invalid action"}

    await db.commit()
    return {"ok": True, "status": signal.status}
