from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .models import Bar


class StrategyContext:
    """Lightweight runtime context passed to strategies."""

    def __init__(self, *, config: dict[str, Any], symbol: str, timeframe: str):
        self.config = config
        self.symbol = symbol
        self.timeframe = timeframe


class Strategy(ABC):
    """Base class for all strategies."""

    name: str = "UnnamedStrategy"

    def __init__(self, ctx: StrategyContext):
        self.ctx = ctx

    def on_start(self) -> None:  # optional
        return

    @abstractmethod
    def on_bar(self, bar: Bar) -> dict[str, Any] | None:
        """Process one bar. Return an optional dict of signals/decisions."""

    def on_finish(self) -> None:  # optional
        return
