from app.config import settings
from app.strategies.base import BaseStrategy, Direction, MarketContext, StrategySignal


class TripleOddsDivergence(BaseStrategy):
    """Triple Odds Divergence strategy.

    Compares three independent probability sources:
    1. Polymarket implied probability (market price)
    2. Bookmaker odds (Pinnacle/Bet365, devigged)
    3. AI prediction (Claude analysis)

    Generates a signal when bookmaker + AI form consensus that
    diverges from Polymarket by more than the threshold.
    """

    name = "triple_odds"

    def __init__(
        self,
        divergence_threshold: float = settings.odds_divergence_threshold,
        agreement_threshold: float = settings.book_ai_agreement_threshold,
        base_size: float = 20.0,
    ):
        self.divergence_threshold = divergence_threshold
        self.agreement_threshold = agreement_threshold
        self.base_size = base_size

    def evaluate(self, context: MarketContext) -> StrategySignal:
        p_poly = context.yes_price
        p_book = context.book_home_prob  # For home win market
        p_ai = context.ai_home_prob

        # Need all three sources
        if p_poly is None or p_book is None or p_ai is None:
            return StrategySignal(
                direction=Direction.NO_BET,
                confidence=0.0,
                suggested_size=0.0,
                strategy_name=self.name,
                reasoning="Missing data source(s)",
            )

        # Check if bookmaker and AI agree
        book_ai_agree = abs(p_book - p_ai) < self.agreement_threshold

        if not book_ai_agree:
            return StrategySignal(
                direction=Direction.NO_BET,
                confidence=0.0,
                suggested_size=0.0,
                strategy_name=self.name,
                poly_prob=p_poly,
                book_prob=p_book,
                ai_prob=p_ai,
                reasoning=f"Book-AI disagreement: {abs(p_book - p_ai):.1%}",
            )

        # Consensus vs Polymarket
        consensus = (p_book + p_ai) / 2
        delta = consensus - p_poly

        if abs(delta) < self.divergence_threshold:
            return StrategySignal(
                direction=Direction.NO_BET,
                confidence=0.0,
                suggested_size=0.0,
                strategy_name=self.name,
                poly_prob=p_poly,
                book_prob=p_book,
                ai_prob=p_ai,
                consensus_delta=delta,
                reasoning=f"Delta {delta:.1%} below threshold",
            )

        # Signal!
        confidence = min(abs(delta) / 0.15, 1.0)
        direction = Direction.BUY_YES if delta > 0 else Direction.BUY_NO
        size = self.base_size * confidence

        return StrategySignal(
            direction=direction,
            confidence=confidence,
            suggested_size=size,
            strategy_name=self.name,
            poly_prob=p_poly,
            book_prob=p_book,
            ai_prob=p_ai,
            consensus_delta=delta,
            reasoning=(
                f"Consensus ({consensus:.1%}) vs Poly ({p_poly:.1%}), "
                f"delta={delta:+.1%}, book={p_book:.1%}, ai={p_ai:.1%}"
            ),
        )
