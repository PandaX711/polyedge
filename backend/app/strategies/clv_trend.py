from app.strategies.base import BaseStrategy, Direction, MarketContext, StrategySignal


class CLVTrendStrategy(BaseStrategy):
    """Closing Line Value trend strategy.

    Tracks price movement from 48h before match to current.
    If price has trended > 8% in one direction and match is > 6h away,
    follows the trend (closing line is the most accurate probability).
    """

    name = "clv_trend"

    def __init__(
        self,
        trend_threshold: float = 0.08,
        base_size: float = 15.0,
    ):
        self.trend_threshold = trend_threshold
        self.base_size = base_size

    def evaluate(self, context: MarketContext) -> StrategySignal:
        price_now = context.yes_price
        price_48h = context.price_48h_ago

        if not price_now or not price_48h or price_48h == 0:
            return StrategySignal(
                direction=Direction.NO_BET,
                confidence=0.0,
                suggested_size=0.0,
                strategy_name=self.name,
                reasoning="Missing price history (need 48h data)",
            )

        trend = (price_now - price_48h) / price_48h

        if abs(trend) < self.trend_threshold:
            return StrategySignal(
                direction=Direction.NO_BET,
                confidence=0.0,
                suggested_size=0.0,
                strategy_name=self.name,
                poly_prob=price_now,
                reasoning=f"Trend {trend:+.1%} below threshold",
            )

        direction = Direction.BUY_YES if trend > 0 else Direction.BUY_NO
        confidence = min(abs(trend) / 0.20, 1.0)
        size = self.base_size * confidence

        return StrategySignal(
            direction=direction,
            confidence=confidence,
            suggested_size=size,
            strategy_name=self.name,
            poly_prob=price_now,
            reasoning=f"48h trend {trend:+.1%}, following closing line momentum",
        )
