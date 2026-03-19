import logging
from dataclasses import dataclass
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class BookmakerOdds:
    """Devigged bookmaker odds as implied probabilities."""

    home_win: float
    draw: float
    away_win: float
    source: str  # e.g. "pinnacle", "bet365"
    raw_home: float  # Original decimal odds
    raw_draw: float
    raw_away: float


class OddsFetcher:
    """Fetch and process odds from The Odds API."""

    BASE_URL = "https://api.the-odds-api.com/v4"

    def __init__(self):
        self.api_key = settings.odds_api_key
        self.client = httpx.AsyncClient(timeout=30.0)

    async def get_match_odds(
        self,
        home_team: str,
        away_team: str,
        sport: str = "soccer_epl",
    ) -> Optional[BookmakerOdds]:
        """Fetch odds for a specific match, prefer Pinnacle."""
        try:
            resp = await self.client.get(
                f"{self.BASE_URL}/sports/{sport}/odds",
                params={
                    "apiKey": self.api_key,
                    "regions": "eu",
                    "markets": "h2h",
                    "bookmakers": "pinnacle,bet365",
                },
            )
            resp.raise_for_status()
            events = resp.json()

            # Find matching event
            for event in events:
                if self._match_teams(event, home_team, away_team):
                    return self._extract_best_odds(event)

            return None
        except httpx.HTTPError as e:
            logger.error("Odds API error: %s", e)
            return None

    def _match_teams(self, event: dict, home: str, away: str) -> bool:
        """Fuzzy match team names."""
        event_home = event.get("home_team", "").lower()
        event_away = event.get("away_team", "").lower()
        return (
            home.lower() in event_home
            or event_home in home.lower()
        ) and (
            away.lower() in event_away
            or event_away in away.lower()
        )

    def _extract_best_odds(self, event: dict) -> Optional[BookmakerOdds]:
        """Extract and devig odds, preferring Pinnacle."""
        bookmakers = event.get("bookmakers", [])
        # Prefer pinnacle
        for bm in bookmakers:
            if bm["key"] == "pinnacle":
                return self._parse_bookmaker(bm)
        # Fallback to first available
        if bookmakers:
            return self._parse_bookmaker(bookmakers[0])
        return None

    def _parse_bookmaker(self, bm: dict) -> Optional[BookmakerOdds]:
        """Parse bookmaker data and remove overround."""
        for market in bm.get("markets", []):
            if market["key"] != "h2h":
                continue
            outcomes = {o["name"]: o["price"] for o in market["outcomes"]}
            home_odds = outcomes.get("Home") or outcomes.get(list(outcomes.keys())[0])
            draw_odds = outcomes.get("Draw")
            away_odds = outcomes.get("Away") or outcomes.get(list(outcomes.keys())[-1])

            if not all([home_odds, draw_odds, away_odds]):
                return None

            # Remove overround (normalize to sum=1)
            raw_probs = [1 / home_odds, 1 / draw_odds, 1 / away_odds]
            total = sum(raw_probs)
            devigged = [p / total for p in raw_probs]

            return BookmakerOdds(
                home_win=devigged[0],
                draw=devigged[1],
                away_win=devigged[2],
                source=bm["key"],
                raw_home=home_odds,
                raw_draw=draw_odds,
                raw_away=away_odds,
            )
        return None

    # Sport key mapping for The Odds API
    LEAGUE_TO_SPORT = {
        "EPL": "soccer_epl",
        "LaLiga": "soccer_spain_la_liga",
        "SerieA": "soccer_italy_serie_a",
        "Bundesliga": "soccer_germany_bundesliga",
        "Ligue1": "soccer_france_ligue_one",
        "UCL": "soccer_uefa_champs_league",
    }

    async def close(self):
        await self.client.aclose()
