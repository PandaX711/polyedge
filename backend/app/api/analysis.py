import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.market import AIReport

router = APIRouter()


class AIReportOut(BaseModel):
    id: int
    condition_id: str
    home_team: Optional[str] = None
    away_team: Optional[str] = None
    prediction: Optional[str] = None
    confidence: Optional[float] = None
    home_win_prob: Optional[float] = None
    draw_prob: Optional[float] = None
    away_win_prob: Optional[float] = None
    key_factors: Optional[list[str]] = None
    reasoning: Optional[str] = None
    model: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[AIReportOut])
async def list_reports(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(AIReport).order_by(AIReport.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    reports = result.scalars().all()

    out = []
    for r in reports:
        factors = None
        if r.key_factors:
            try:
                factors = json.loads(r.key_factors)
            except json.JSONDecodeError:
                factors = [r.key_factors]
        out.append(
            AIReportOut(
                id=r.id,
                condition_id=r.condition_id,
                home_team=r.home_team,
                away_team=r.away_team,
                prediction=r.prediction,
                confidence=r.confidence,
                home_win_prob=r.home_win_prob,
                draw_prob=r.draw_prob,
                away_win_prob=r.away_win_prob,
                key_factors=factors,
                reasoning=r.reasoning,
                model=r.model,
                created_at=r.created_at,
            )
        )
    return out


@router.get("/{condition_id}", response_model=Optional[AIReportOut])
async def get_report(condition_id: str, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(AIReport)
        .where(AIReport.condition_id == condition_id)
        .order_by(AIReport.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    report = result.scalar_one_or_none()
    if not report:
        return None

    factors = None
    if report.key_factors:
        try:
            factors = json.loads(report.key_factors)
        except json.JSONDecodeError:
            factors = [report.key_factors]

    return AIReportOut(
        id=report.id,
        condition_id=report.condition_id,
        home_team=report.home_team,
        away_team=report.away_team,
        prediction=report.prediction,
        confidence=report.confidence,
        home_win_prob=report.home_win_prob,
        draw_prob=report.draw_prob,
        away_win_prob=report.away_win_prob,
        key_factors=factors,
        reasoning=report.reasoning,
        model=report.model,
        created_at=report.created_at,
    )
