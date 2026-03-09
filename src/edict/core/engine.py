from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from rich.console import Console

from .models import Bar
from .strategy import Strategy


class Engine:
    def __init__(self, *, console: Console | None = None):
        self.console = console or Console()

    def run(self, strategy: Strategy, bars: Iterable[Bar]) -> list[dict[str, Any]]:
        """Run a strategy over a stream of bars, collecting emitted signals."""

        out: list[dict[str, Any]] = []
        strategy.on_start()
        for bar in bars:
            signal = strategy.on_bar(bar)
            if signal is not None:
                out.append(signal)
        strategy.on_finish()
        return out
