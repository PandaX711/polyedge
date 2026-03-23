"""Day 0 Alpha Validation Script.

Fetches World Cup markets from Polymarket and odds from The Odds API (Pinnacle),
computes divergences, and outputs a go/no-go table.

Decision criteria:
  - If median divergence > 5%: FULL SPEED AHEAD
  - If median divergence 3-5%: PROCEED WITH CAUTION
  - If median divergence < 3%: PIVOT — alpha may not exist

Usage:
  cd backend
  .venv/bin/python -m scripts.alpha_validation
"""

import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path

# Add parent to path so we can import app modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx

GAMMA_URL = "https://gamma-api.polymarket.com"
ODDS_API_URL = "https://api.the-odds-api.com/v4"


@dataclass
class MarketComparison:
    team: str
    poly_yes: float  # Polymarket YES price (implied probability)
    pinnacle_prob: float | None  # Pinnacle implied probability (devigged)
    divergence: float | None  # pinnacle - poly
    volume: float
    liquidity: float


async def fetch_polymarket_wc_markets(client: httpx.AsyncClient) -> list[dict]:
    """Fetch World Cup winner markets from Polymarket."""
    resp = await client.get(
        f"{GAMMA_URL}/markets",
        params={"tag": "world-cup", "active": "true", "closed": "false", "limit": 200},
    )
    resp.raise_for_status()
    markets = resp.json()
    # Filter to "Will X win the 2026 FIFA World Cup?" pattern
    wc_markets = [
        m for m in markets
        if "win the 2026 FIFA World Cup" in m.get("question", "")
        or "qualify for the 2026 FIFA World Cup" in m.get("question", "")
    ]
    return wc_markets


async def fetch_pinnacle_wc_odds(client: httpx.AsyncClient, api_key: str) -> dict[str, float]:
    """Fetch World Cup winner odds from Pinnacle via The Odds API."""
    if not api_key:
        return {}

    team_probs: dict[str, float] = {}
    sport = "soccer_fifa_world_cup_winner"

    try:
        resp = await client.get(
            f"{ODDS_API_URL}/sports/{sport}/odds",
            params={
                "apiKey": api_key,
                "regions": "eu",
                "markets": "outrights",
                "bookmakers": "pinnacle",
            },
        )
        if resp.status_code == 404:
            # Try alternative sport key
            resp = await client.get(
                f"{ODDS_API_URL}/sports/soccer_fifa_world_cup/odds",
                params={
                    "apiKey": api_key,
                    "regions": "eu",
                    "markets": "outrights",
                    "bookmakers": "pinnacle",
                },
            )

        if resp.status_code != 200:
            print(f"  ⚠️  Odds API returned {resp.status_code}: {resp.text[:200]}")
            remaining = resp.headers.get("x-requests-remaining", "?")
            print(f"  ℹ️  API requests remaining: {remaining}")
            return {}

        remaining = resp.headers.get("x-requests-remaining", "?")
        print(f"  ℹ️  Odds API requests remaining: {remaining}")

        events = resp.json()
        for event in events:
            for bm in event.get("bookmakers", []):
                if bm["key"] != "pinnacle":
                    continue
                for market in bm.get("markets", []):
                    if market["key"] not in ("outrights", "h2h"):
                        continue
                    # Devig: normalize to sum=1
                    outcomes = market.get("outcomes", [])
                    raw_probs = []
                    names = []
                    for o in outcomes:
                        raw_probs.append(1.0 / o["price"])
                        names.append(o["name"])
                    total = sum(raw_probs)
                    for name, prob in zip(names, raw_probs):
                        team_probs[name.lower()] = prob / total

    except httpx.HTTPError as e:
        print(f"  ⚠️  Odds API error: {e}")

    return team_probs


def extract_team_name(question: str) -> str:
    """Extract team name from market question."""
    # "Will Brazil win the 2026 FIFA World Cup?"
    q = question.replace("Will ", "").replace(" win the 2026 FIFA World Cup?", "")
    q = q.replace(" qualify for the 2026 FIFA World Cup?", "")
    return q.strip()


def extract_price(market: dict) -> tuple[float | None, float | None]:
    """Extract YES/NO prices from market data."""
    outcome_prices = market.get("outcomePrices")
    if outcome_prices:
        try:
            prices = json.loads(outcome_prices) if isinstance(outcome_prices, str) else outcome_prices
            return float(prices[0]), float(prices[1]) if len(prices) > 1 else None
        except (json.JSONDecodeError, IndexError, ValueError):
            pass

    tokens = market.get("tokens", [])
    yes_price = None
    no_price = None
    for t in tokens:
        outcome = (t.get("outcome") or "").upper()
        price_val = t.get("price")
        if price_val is not None:
            if outcome == "YES":
                yes_price = float(price_val)
            elif outcome == "NO":
                no_price = float(price_val)
    return yes_price, no_price


def fuzzy_match_team(poly_team: str, pinnacle_teams: dict[str, float]) -> float | None:
    """Fuzzy match Polymarket team name to Pinnacle team name."""
    poly_lower = poly_team.lower().strip()
    # Direct match
    if poly_lower in pinnacle_teams:
        return pinnacle_teams[poly_lower]
    # Partial match
    for pin_name, prob in pinnacle_teams.items():
        if poly_lower in pin_name or pin_name in poly_lower:
            return prob
    return None


async def main():
    print("=" * 70)
    print("  PolyEdge Day 0 Alpha Validation")
    print("  Polymarket vs Pinnacle — World Cup 2026 Divergence Analysis")
    print("=" * 70)
    print()

    # Load API key from .env
    import dotenv
    env_path = Path(__file__).resolve().parent.parent / ".env"
    env = dotenv.dotenv_values(env_path)
    odds_api_key = env.get("ODDS_API_KEY", "")

    async with httpx.AsyncClient(timeout=30.0) as client:
        print("[1/3] Fetching Polymarket World Cup markets...")
        pm_markets = await fetch_polymarket_wc_markets(client)
        print(f"  Found {len(pm_markets)} World Cup markets")

        print("\n[2/3] Fetching Pinnacle odds...")
        if odds_api_key:
            pin_odds = await fetch_pinnacle_wc_odds(client, odds_api_key)
            print(f"  Found {len(pin_odds)} teams with Pinnacle odds")
        else:
            print("  ⚠️  No ODDS_API_KEY in .env — running Polymarket-only analysis")
            pin_odds = {}

        print("\n[3/3] Computing divergences...\n")

        comparisons: list[MarketComparison] = []
        for m in pm_markets:
            team = extract_team_name(m.get("question", ""))
            yes_price, _ = extract_price(m)
            if yes_price is None:
                continue

            pin_prob = fuzzy_match_team(team, pin_odds) if pin_odds else None
            divergence = (pin_prob - yes_price) if pin_prob is not None else None

            comparisons.append(MarketComparison(
                team=team,
                poly_yes=yes_price,
                pinnacle_prob=pin_prob,
                divergence=divergence,
                volume=float(m.get("volume", 0) or 0),
                liquidity=float(m.get("liquidity", 0) or 0),
            ))

        # Sort by volume (most liquid first)
        comparisons.sort(key=lambda c: c.volume, reverse=True)

        # Print table
        print(f"{'Team':<25} {'Poly':>7} {'Pinnacle':>10} {'Delta':>8} {'Volume':>12} {'Liquid':>10}")
        print("-" * 75)

        matched = 0
        divergences = []
        for c in comparisons[:30]:  # Top 30 by volume
            pin_str = f"{c.pinnacle_prob*100:.1f}%" if c.pinnacle_prob is not None else "—"
            div_str = f"{c.divergence*100:+.1f}%" if c.divergence is not None else "—"
            vol_str = f"${c.volume/1000:.1f}K" if c.volume >= 1000 else f"${c.volume:.0f}"
            liq_str = f"${c.liquidity/1000:.1f}K" if c.liquidity >= 1000 else f"${c.liquidity:.0f}"

            # Color-code divergence
            if c.divergence is not None:
                matched += 1
                divergences.append(abs(c.divergence))
                if abs(c.divergence) >= 0.05:
                    div_str = f"🔴 {div_str}"
                elif abs(c.divergence) >= 0.03:
                    div_str = f"🟡 {div_str}"
                else:
                    div_str = f"🟢 {div_str}"

            print(f"{c.team:<25} {c.poly_yes*100:>6.1f}% {pin_str:>10} {div_str:>12} {vol_str:>12} {liq_str:>10}")

        # Summary
        print()
        print("=" * 70)
        print("  SUMMARY")
        print("=" * 70)
        print(f"  Total Polymarket WC markets: {len(comparisons)}")
        print(f"  Matched with Pinnacle:       {matched}")

        if divergences:
            divergences.sort(reverse=True)
            median_div = divergences[len(divergences) // 2]
            avg_div = sum(divergences) / len(divergences)
            max_div = divergences[0]
            above_5pct = sum(1 for d in divergences if d >= 0.05)
            above_3pct = sum(1 for d in divergences if d >= 0.03)

            print(f"  Median absolute divergence:  {median_div*100:.1f}%")
            print(f"  Average absolute divergence: {avg_div*100:.1f}%")
            print(f"  Max divergence:              {max_div*100:.1f}%")
            print(f"  Markets with |delta| > 5%:   {above_5pct}")
            print(f"  Markets with |delta| > 3%:   {above_3pct}")
            print()

            if median_div >= 0.05:
                print("  🟢 VERDICT: FULL SPEED AHEAD")
                print("     Significant divergences detected. Alpha likely exists.")
            elif median_div >= 0.03:
                print("  🟡 VERDICT: PROCEED WITH CAUTION")
                print("     Moderate divergences. Alpha may exist but margins are thin.")
            else:
                print("  🔴 VERDICT: CONSIDER PIVOTING")
                print("     Small divergences. Polymarket may be efficiently priced.")
        else:
            print()
            if not odds_api_key:
                print("  ⚠️  Cannot compute verdict without Pinnacle odds.")
                print("     Add ODDS_API_KEY to backend/.env to enable comparison.")
                print()
                print("  Polymarket-only insights:")
                total_vol = sum(c.volume for c in comparisons)
                total_liq = sum(c.liquidity for c in comparisons)
                print(f"  Total WC market volume:    ${total_vol/1e6:.1f}M")
                print(f"  Total WC market liquidity: ${total_liq/1e6:.1f}M")
                top_5 = comparisons[:5]
                print(f"  Top 5 by volume: {', '.join(c.team for c in top_5)}")
            else:
                print("  ⚠️  No matched markets. Check team name matching.")

        print()


if __name__ == "__main__":
    asyncio.run(main())
