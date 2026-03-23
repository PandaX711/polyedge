import json
import logging
from datetime import datetime, timedelta

from sqlalchemy import func, select

from app.config import settings
from app.database import async_session
from app.models.market import AIReport, Market, Price, Signal
from app.services.odds_fetcher import OddsFetcher
from app.services.polymarket import GammaClient
from app.strategies.base import Direction, MarketContext
from app.strategies.clv_trend import CLVTrendStrategy
from app.strategies.odds_divergence import TripleOddsDivergence
from app.strategies.volume_spike import VolumeSpikeStrategy

logger = logging.getLogger(__name__)

gamma = GammaClient()
odds_fetcher = OddsFetcher()

strategies = [
    TripleOddsDivergence(),
    VolumeSpikeStrategy(),
    CLVTrendStrategy(),
]


def _parse_teams(question: str) -> tuple[str, str]:
    """Try to extract home/away teams from market question."""
    # Match format: "Will X win the 2026 FIFA World Cup?"
    if "win the" in question and "?" in question:
        team = question.replace("Will ", "").split(" win the")[0].strip()
        return team, ""
    # Match format: "Will X qualify for the 2026 FIFA World Cup?"
    if "qualify for" in question and "?" in question:
        team = question.replace("Will ", "").split(" qualify for")[0].strip()
        return team, ""
    # Common patterns: "Team A vs Team B", "Team A v Team B"
    for sep in [" vs ", " v ", " vs. "]:
        if sep in question:
            parts = question.split(sep, 1)
            home = parts[0].strip().split(":")[-1].strip()
            away = parts[1].strip().split("?")[0].strip()
            return home, away
    return question, ""


# Keywords that indicate a football/soccer market
_FOOTBALL_KEYWORDS = [
    "world cup", "fifa", "premier league", "epl", "la liga", "laliga",
    "serie a", "seriea", "bundesliga", "ligue 1", "ligue1",
    "champions league", "ucl", "europa league", "mls", "copa america",
    "euro 2026", "nations league", "fa cup", "carabao", "community shield",
    "ballon d'or", "golden boot", "football", "soccer",
    # Common football team names as fallback
    "manchester", "liverpool", "arsenal", "chelsea", "barcelona", "real madrid",
    "bayern", "juventus", "psg", "inter milan", "ac milan", "dortmund",
    "atletico", "napoli", "tottenham", "man city",
]


def _is_football_market(question: str, slug: str = "", tags: list[str] | None = None) -> bool:
    """Check if a market is football/soccer related."""
    text = f"{question} {slug}".lower()
    if tags:
        text += " " + " ".join(t.lower() for t in tags)
    return any(kw in text for kw in _FOOTBALL_KEYWORDS)


def _detect_league(question: str, slug: str = "") -> str:
    """Detect league from market question or slug."""
    text = f"{question} {slug}".lower()
    if any(k in text for k in ["premier league", "epl", "english"]):
        return "EPL"
    if any(k in text for k in ["la liga", "laliga", "spanish"]):
        return "LaLiga"
    if any(k in text for k in ["serie a", "seriea", "italian"]):
        return "SerieA"
    if any(k in text for k in ["bundesliga", "german"]):
        return "Bundesliga"
    if any(k in text for k in ["ligue 1", "ligue1", "french"]):
        return "Ligue1"
    if any(k in text for k in ["champions league", "ucl"]):
        return "UCL"
    if any(k in text for k in ["world cup", "fifa", "worldcup"]):
        return "WorldCup"
    return "Other"


def _detect_market_type(question: str) -> str:
    """Detect if this is a binary or multi-outcome market."""
    q = question.lower()
    if "win the" in q or "winner" in q:
        return "winner"
    if "qualify" in q:
        return "qualifier"
    if " vs " in q or " v " in q:
        return "match"
    return "binary"


async def scan_markets():
    """Scan Polymarket for football markets and upsert to DB."""
    logger.info("Scanning Polymarket for football markets...")
    raw_markets = await gamma.get_football_markets(limit=200)
    logger.info("Found %d raw markets", len(raw_markets))

    count = 0
    skipped = 0
    async with async_session() as db:
        for m in raw_markets:
            condition_id = m.get("conditionId") or m.get("condition_id", "")
            if not condition_id:
                continue

            question = m.get("question", "")
            slug = m.get("slug", "")
            tags = m.get("tags", [])

            # Filter: only keep football/soccer markets
            if not _is_football_market(question, slug, tags):
                skipped += 1
                continue

            home, away = _parse_teams(question)
            league = _detect_league(question, slug)
            market_type = _detect_market_type(question)

            # Upsert
            stmt = select(Market).where(Market.condition_id == condition_id)
            result = await db.execute(stmt)
            existing = result.scalar_one_or_none()

            tokens = m.get("tokens", [])
            yes_token = tokens[0].get("token_id", "") if tokens else ""
            no_token = tokens[1].get("token_id", "") if len(tokens) > 1 else ""

            if existing:
                existing.volume = float(m.get("volume", 0) or 0)
                existing.liquidity = float(m.get("liquidity", 0) or 0)
                existing.active = 1 if m.get("active") else 0
                existing.updated_at = datetime.utcnow()
            else:
                market = Market(
                    condition_id=condition_id,
                    question=question,
                    slug=slug,
                    sport="football",
                    league=league,
                    market_type=market_type,
                    home_team=home,
                    away_team=away,
                    yes_token_id=yes_token,
                    no_token_id=no_token,
                    volume=float(m.get("volume", 0) or 0),
                    liquidity=float(m.get("liquidity", 0) or 0),
                    active=1 if m.get("active") else 0,
                )
                db.add(market)
            count += 1

        await db.commit()
    logger.info("Market scan complete: %d football markets saved, %d non-football skipped", count, skipped)


async def collect_prices():
    """Collect current prices by re-fetching all football markets from Gamma API.

    Uses the batch listing endpoint (same as scan_markets) to get prices
    in bulk, avoiding per-market API calls that may 422.
    """
    logger.info("Collecting prices...")
    raw_markets = await gamma.get_football_markets(limit=200)
    count = 0

    async with async_session() as db:
        for m in raw_markets:
            condition_id = m.get("conditionId") or m.get("condition_id", "")
            if not condition_id:
                continue

            # Extract price from tokens or outcomePrices
            tokens = m.get("tokens", [])
            outcome_prices = m.get("outcomePrices")

            yes_price = None
            no_price = None

            if outcome_prices:
                try:
                    prices = json.loads(outcome_prices) if isinstance(outcome_prices, str) else outcome_prices
                    yes_price = float(prices[0]) if prices else None
                    no_price = float(prices[1]) if len(prices) > 1 else None
                except (json.JSONDecodeError, IndexError, ValueError):
                    pass

            if yes_price is None and tokens:
                for t in tokens:
                    outcome = (t.get("outcome") or "").upper()
                    price_val = t.get("price")
                    if price_val is not None:
                        if outcome == "YES" or (yes_price is None and outcome != "NO"):
                            yes_price = float(price_val)
                        elif outcome == "NO":
                            no_price = float(price_val)

            if yes_price is None or yes_price == 0:
                continue

            price = Price(
                condition_id=condition_id,
                yes_price=yes_price,
                no_price=no_price,
                volume_1h=float(m.get("volume", 0) or 0),
            )
            db.add(price)
            count += 1

        await db.commit()
    logger.info("Price collection complete: %d prices recorded", count)


async def run_strategies():
    """Run all strategies against active markets."""
    logger.info("Running strategies...")
    async with async_session() as db:
        stmt = select(Market).where(Market.active == 1)
        result = await db.execute(stmt)
        markets = result.scalars().all()

        for m in markets:
            # Get latest price
            price_stmt = (
                select(Price)
                .where(Price.condition_id == m.condition_id)
                .order_by(Price.timestamp.desc())
                .limit(1)
            )
            price_result = await db.execute(price_stmt)
            latest_price = price_result.scalar_one_or_none()
            if not latest_price:
                continue

            # Get 48h ago price
            cutoff = datetime.utcnow() - timedelta(hours=48)
            old_price_stmt = (
                select(Price)
                .where(Price.condition_id == m.condition_id)
                .where(Price.timestamp <= cutoff)
                .order_by(Price.timestamp.desc())
                .limit(1)
            )
            old_result = await db.execute(old_price_stmt)
            old_price = old_result.scalar_one_or_none()

            # Get 24h avg volume
            vol_cutoff = datetime.utcnow() - timedelta(hours=24)
            vol_stmt = select(func.avg(Price.volume_1h)).where(
                Price.condition_id == m.condition_id,
                Price.timestamp >= vol_cutoff,
            )
            vol_result = await db.execute(vol_stmt)
            avg_vol = vol_result.scalar()

            # Get latest AI report
            ai_stmt = (
                select(AIReport)
                .where(AIReport.condition_id == m.condition_id)
                .order_by(AIReport.created_at.desc())
                .limit(1)
            )
            ai_result = await db.execute(ai_stmt)
            ai_report = ai_result.scalar_one_or_none()

            # Get bookmaker odds
            sport_key = odds_fetcher.LEAGUE_TO_SPORT.get(m.league or "", "soccer_epl")
            book_odds = None
            if m.home_team and m.away_team and settings.odds_api_key:
                book_odds = await odds_fetcher.get_match_odds(
                    m.home_team, m.away_team, sport_key
                )

            context = MarketContext(
                condition_id=m.condition_id,
                question=m.question or "",
                home_team=m.home_team or "",
                away_team=m.away_team or "",
                league=m.league or "",
                yes_price=latest_price.yes_price,
                book_home_prob=book_odds.home_win if book_odds else None,
                book_draw_prob=book_odds.draw if book_odds else None,
                book_away_prob=book_odds.away_win if book_odds else None,
                ai_home_prob=ai_report.home_win_prob if ai_report else None,
                ai_draw_prob=ai_report.draw_prob if ai_report else None,
                ai_away_prob=ai_report.away_win_prob if ai_report else None,
                volume_1h=latest_price.volume_1h,
                volume_24h_avg=float(avg_vol) if avg_vol else None,
                price_48h_ago=old_price.yes_price if old_price else None,
            )

            for strategy in strategies:
                signal = strategy.evaluate(context)
                if signal.direction != Direction.NO_BET:
                    db_signal = Signal(
                        condition_id=m.condition_id,
                        strategy=signal.strategy_name,
                        direction=signal.direction.value,
                        confidence=signal.confidence,
                        suggested_size=signal.suggested_size,
                        poly_prob=signal.poly_prob,
                        book_prob=signal.book_prob,
                        ai_prob=signal.ai_prob,
                        consensus_delta=signal.consensus_delta,
                    )
                    db.add(db_signal)
                    logger.info(
                        "Signal: %s %s on %s (conf=%.2f)",
                        signal.direction.value,
                        signal.strategy_name,
                        m.condition_id[:12],
                        signal.confidence,
                    )

        await db.commit()
    logger.info("Strategy run complete")
