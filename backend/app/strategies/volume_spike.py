from app.strategies.base import BaseStrategy, Direction, MarketContext, StrategySignal


class VolumeSpikeStrategy(BaseStrategy):
    """Volume Spike strategy.

    Detects abnormal volume inflows on Polymarket markets.
    When current 1h volume > 3x the 24h average AND price moves > 5%,
    generates a signal following the smart money direction.
    """

    name = "volume_spike"

    def __init__(
        self,
        volume_multiplier: float = 3.0,
        price_change_threshold: float = 0.05,
        base_size: float = 15.0,
    ):
        self.volume_multiplier = volume_multiplier
        self.price_change_threshold = price_change_threshold
        self.base_size = base_size

    def evaluate(self, context: MarketContext) -> StrategySignal:
        vol_1h = context.volume_1h
        vol_24h_avg = context.volume_24h_avg
        price_now = context.yes_price
        price_48h = context.price_48h_ago

        if not all([vol_1h, vol_24h_avg, price_now, price_48h]):
            return StrategySignal(
                direction=Direction.NO_BET,
                confidence=0.0,
                suggested_size=0.0,
                strategy_name=self.name,
                reasoning="Missing volume/price data",
            )

        if vol_24h_avg == 0:
            return StrategySignal(
                direction=Direction.NO_BET,
                confidence=0.0,
                suggested_size=0.0,
                strategy_name=self.name,
                reasoning="No baseline volume",
            )

        vol_ratio = vol_1h / vol_24h_avg
        price_change = (price_now - price_48h) / price_48h if price_48h else 0

        if vol_ratio < self.volume_multiplier:
            return StrategySignal(
                direction=Direction.NO_BET,
                confidence=0.0,
                suggested_size=0.0,
                strategy_name=self.name,
                reasoning=f"Volume ratio {vol_ratio:.1f}x below threshold",
            )

        if abs(price_change) < self.price_change_threshold:
            return StrategySignal(
                direction=Direction.NO_BET,
                confidence=0.0,
                suggested_size=0.0,
                strategy_name=self.name,
                reasoning=f"Price change {price_change:.1%} below threshold",
            )

        # Follow the money on positive moves, fade on negative
        if price_change > 0:
            direction = Direction.BUY_YES
        else:
            direction = Direction.BUY_NO

        confidence = min(vol_ratio / 6.0, 1.0) * min(abs(price_change) / 0.15, 1.0)
        size = self.base_size * confidence

        return StrategySignal(
            direction=direction,
            confidence=confidence,
            suggested_size=size,
            strategy_name=self.name,
            poly_prob=price_now,
            reasoning=(
                f"Volume spike {vol_ratio:.1f}x, price change {price_change:+.1%}"
            ),
        )
