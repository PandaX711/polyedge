import json
import logging
from dataclasses import dataclass
from typing import Optional

import anthropic

from app.ai.prompts import MATCH_ANALYSIS_PROMPT
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


@dataclass
class AIAnalysis:
    prediction: str
    confidence: float
    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    implied_odds: dict
    vs_polymarket: dict
    key_factors: list[str]
    reasoning: str
    raw_response: str


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
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )

            raw = response.content[0].text
            data = json.loads(raw)

            return AIAnalysis(
                prediction=data["prediction"],
                confidence=data["confidence"],
                home_win_prob=data["probabilities"]["home_win"],
                draw_prob=data["probabilities"]["draw"],
                away_win_prob=data["probabilities"]["away_win"],
                implied_odds=data.get("implied_odds", {}),
                vs_polymarket=data.get("vs_polymarket", {}),
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
