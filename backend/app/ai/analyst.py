import json
import logging
from dataclasses import dataclass, field
from typing import Optional

import anthropic

from app.ai.prompts import MATCH_ANALYSIS_PROMPT, WC_WINNER_ANALYSIS_PROMPT
from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class MatchData:
    home_team: str
    away_team: str
    league: str
    round: str
    date: str
    home_recent_5: str
    home_rank: str
    home_points: str
    home_record: str
    home_injuries: str
    away_recent_5: str
    away_rank: str
    away_points: str
    away_record: str
    away_injuries: str
    h2h: str
    pm_home: str
    pm_draw: str
    pm_away: str
    pin_home: str
    pin_draw: str
    pin_away: str
    # Polymarket trading signals
    pm_spread: str = "N/A"
    pm_price_change: str = "N/A"
    pm_volume_1h: str = "0"
    pm_volume_avg: str = "0"
    pm_volume_ratio: str = "1.0"


@dataclass
class AIAnalysis:
    prediction: str
    confidence: float
    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    implied_odds: dict = field(default_factory=dict)
    vs_polymarket: dict = field(default_factory=dict)
    market_signals: dict = field(default_factory=dict)
    key_factors: list[str] = field(default_factory=list)
    reasoning: str = ""
    raw_response: str = ""


@dataclass
class WCWinnerAnalysis:
    most_undervalued: list[dict] = field(default_factory=list)
    most_overvalued: list[dict] = field(default_factory=list)
    dark_horses: list[dict] = field(default_factory=list)
    top_recommendation: dict = field(default_factory=dict)
    market_overview: str = ""
    raw_response: str = ""


def _validate_probabilities(probs: dict) -> dict:
    """Ensure probabilities sum to ~1.0, normalize if needed."""
    hw = probs.get("home_win", 0)
    dr = probs.get("draw", 0)
    aw = probs.get("away_win", 0)
    total = hw + dr + aw

    if total == 0:
        return {"home_win": 0.33, "draw": 0.34, "away_win": 0.33}

    if abs(total - 1.0) > 0.05:
        logger.warning("AI probs sum=%.3f, normalizing (was h=%.3f d=%.3f a=%.3f)", total, hw, dr, aw)
        hw /= total
        dr /= total
        aw /= total

    return {"home_win": round(hw, 4), "draw": round(dr, 4), "away_win": round(aw, 4)}


class MatchAnalyst:
    """LLM-powered match analysis using Claude."""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.ai_model

    async def analyze(self, match: MatchData) -> Optional[AIAnalysis]:
        """Analyze a match and return structured prediction."""
        prompt = MATCH_ANALYSIS_PROMPT.format(
            home_team=match.home_team,
            away_team=match.away_team,
            league=match.league,
            round=match.round,
            date=match.date,
            home_recent_5=match.home_recent_5,
            home_rank=match.home_rank,
            home_points=match.home_points,
            home_record=match.home_record,
            home_injuries=match.home_injuries,
            away_recent_5=match.away_recent_5,
            away_rank=match.away_rank,
            away_points=match.away_points,
            away_record=match.away_record,
            away_injuries=match.away_injuries,
            h2h=match.h2h,
            pm_home=match.pm_home,
            pm_draw=match.pm_draw,
            pm_away=match.pm_away,
            pin_home=match.pin_home,
            pin_draw=match.pin_draw,
            pin_away=match.pin_away,
            pm_spread=match.pm_spread,
            pm_price_change=match.pm_price_change,
            pm_volume_1h=match.pm_volume_1h,
            pm_volume_avg=match.pm_volume_avg,
            pm_volume_ratio=match.pm_volume_ratio,
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}],
            )

            raw = response.content[0].text
            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            data = json.loads(raw)

            probs = _validate_probabilities(data.get("probabilities", {}))

            return AIAnalysis(
                prediction=data["prediction"],
                confidence=data["confidence"],
                home_win_prob=probs["home_win"],
                draw_prob=probs["draw"],
                away_win_prob=probs["away_win"],
                implied_odds=data.get("implied_odds", {}),
                vs_polymarket=data.get("vs_polymarket", {}),
                market_signals=data.get("market_signals", {}),
                key_factors=data.get("key_factors", []),
                reasoning=data.get("reasoning", ""),
                raw_response=raw,
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("Failed to parse AI response: %s", e)
            return None
        except anthropic.APIError as e:
            logger.error("Anthropic API error: %s", e)
            return None

    async def analyze_wc_winner(
        self, outcomes: list[dict], total_volume: float, total_liquidity: float
    ) -> Optional[WCWinnerAnalysis]:
        """Analyze World Cup winner market using multi-outcome data."""
        from datetime import datetime

        top_n = min(len(outcomes), 20)
        table_lines = []
        prob_sum = 0.0
        for o in outcomes[:top_n]:
            pct = o["yes_price"] * 100
            prob_sum += pct
            vol = o["volume"]
            vol_str = f"${vol/1e6:.1f}M" if vol >= 1e6 else f"${vol/1e3:.0f}K"
            table_lines.append(f"  {o['team']:20s} {pct:5.1f}%  交易量={vol_str}")

        prompt = WC_WINNER_ANALYSIS_PROMPT.format(
            date=datetime.utcnow().strftime("%Y-%m-%d"),
            top_n=top_n,
            team_odds_table="\n".join(table_lines),
            total_volume=f"{total_volume/1e6:.1f}M",
            total_liquidity=f"{total_liquidity/1e6:.1f}M",
            prob_sum=f"{prob_sum:.1f}",
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )

            raw = response.content[0].text
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            data = json.loads(raw)

            return WCWinnerAnalysis(
                most_undervalued=data.get("most_undervalued", []),
                most_overvalued=data.get("most_overvalued", []),
                dark_horses=data.get("dark_horses", []),
                top_recommendation=data.get("top_recommendation", {}),
                market_overview=data.get("market_overview", ""),
                raw_response=raw,
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("Failed to parse WC winner AI response: %s", e)
            return None
        except anthropic.APIError as e:
            logger.error("Anthropic API error (WC winner): %s", e)
            return None
