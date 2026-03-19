from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Direction(str, Enum):
    BUY_YES = "BUY_YES"
    BUY_NO = "BUY_NO"
    NO_BET = "NO_BET"


@dataclass
class StrategySignal:
    direction: Direction
    confidence: float  # 0.0 - 1.0
    suggested_size: float  # USDC
    strategy_name: str
    poly_prob: Optional[float] = None
    book_prob: Optional[float] = None
    ai_prob: Optional[float] = None
    consensus_delta: Optional[float] = None
    reasoning: str = ""


@dataclass
class MarketContext:
    condition_id: str
    question: str
    home_team: str
    away_team: str
    league: str
    yes_price: float  # Polymarket implied prob
    book_home_prob: Optional[float] = None
    book_draw_prob: Optional[float] = None
    book_away_prob: Optional[float] = None
    ai_home_prob: Optional[float] = None
    ai_draw_prob: Optional[float] = None
    ai_away_prob: Optional[float] = None
    volume_1h: Optional[float] = None
    volume_24h_avg: Optional[float] = None
    price_48h_ago: Optional[float] = None


class BaseStrategy(ABC):
    """Base class for all strategies."""

    name: str = "base"

    @abstractmethod
    def evaluate(self, context: MarketContext) -> StrategySignal:
        """Evaluate market and return a signal."""
        ...
