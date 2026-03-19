import logging
from typing import Optional

import httpx

from app.ai.analyst import MatchData
from app.config import settings

logger = logging.getLogger(__name__)


class FootballDataAssembler:
    """Assemble match context data from football-data.org for AI analysis."""

    BASE_URL = "https://api.football-data.org/v4"

    LEAGUE_CODES = {
        "EPL": "PL",
        "LaLiga": "PD",
        "SerieA": "SA",
        "Bundesliga": "BL1",
        "Ligue1": "FL1",
        "UCL": "CL",
    }

    def __init__(self):
        self.api_key = settings.football_data_api_key
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={"X-Auth-Token": self.api_key} if self.api_key else {},
        )

    async def assemble(
        self,
        home_team: str,
        away_team: str,
        league: str,
        match_date: str,
        pm_probs: dict,
        pin_probs: dict,
    ) -> Optional[MatchData]:
        """Assemble all context data for a match."""
        league_code = self.LEAGUE_CODES.get(league, "PL")

        standings = await self._get_standings(league_code)
        home_info = self._find_team(standings, home_team)
        away_info = self._find_team(standings, away_team)

        return MatchData(
            home_team=home_team,
            away_team=away_team,
            league=league,
            round=home_info.get("matchday", "N/A") if home_info else "N/A",
            date=match_date,
            home_recent_5=home_info.get("form", "N/A") if home_info else "N/A",
            home_rank=str(home_info.get("position", "N/A")) if home_info else "N/A",
            home_points=str(home_info.get("points", "N/A")) if home_info else "N/A",
            home_record=self._format_record(home_info, "home") if home_info else "N/A",
            home_injuries="暂无数据",  # TODO: integrate injury API
            away_recent_5=away_info.get("form", "N/A") if away_info else "N/A",
            away_rank=str(away_info.get("position", "N/A")) if away_info else "N/A",
            away_points=str(away_info.get("points", "N/A")) if away_info else "N/A",
            away_record=self._format_record(away_info, "away") if away_info else "N/A",
            away_injuries="暂无数据",
            h2h="暂无数据",  # TODO: integrate H2H data
            pm_home=f"{pm_probs.get('home', 0) * 100:.1f}",
            pm_draw=f"{pm_probs.get('draw', 0) * 100:.1f}",
            pm_away=f"{pm_probs.get('away', 0) * 100:.1f}",
            pin_home=f"{pin_probs.get('home', 0) * 100:.1f}",
            pin_draw=f"{pin_probs.get('draw', 0) * 100:.1f}",
            pin_away=f"{pin_probs.get('away', 0) * 100:.1f}",
        )

    async def _get_standings(self, league_code: str) -> list[dict]:
        """Get current league standings."""
        try:
            resp = await self.client.get(
                f"{self.BASE_URL}/competitions/{league_code}/standings"
            )
            resp.raise_for_status()
            data = resp.json()
            standings = data.get("standings", [])
            if standings:
                return standings[0].get("table", [])
            return []
        except httpx.HTTPError as e:
            logger.error("football-data.org error: %s", e)
            return []

    def _find_team(self, standings: list[dict], team_name: str) -> Optional[dict]:
        """Find team in standings by fuzzy name match."""
        team_lower = team_name.lower()
        for entry in standings:
            team = entry.get("team", {})
            name = team.get("name", "").lower()
            short = team.get("shortName", "").lower()
            if team_lower in name or name in team_lower or team_lower in short:
                return entry
        return None

    def _format_record(self, team_info: dict, venue: str) -> str:
        """Format home/away record string."""
        if not team_info:
            return "N/A"
        key = "home" if venue == "home" else "away"
        record = team_info.get(key, {})
        if not record:
            return "N/A"
        w = record.get("won", 0)
        d = record.get("draw", 0)
        l = record.get("lost", 0)
        gf = record.get("goalsFor", 0)
        ga = record.get("goalsAgainst", 0)
        return f"{w}胜{d}平{l}负 (进{gf}/失{ga})"

    async def close(self):
        await self.client.aclose()
