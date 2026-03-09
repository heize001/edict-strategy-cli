from __future__ import annotations

from typing import Any, Dict, Optional

from edict.core.models import Bar
from edict.core.strategy import Strategy


class DemoStrategy(Strategy):
    name = "demo"

    def on_bar(self, bar: Bar) -> Optional[Dict[str, Any]]:
        # Example: emit a trivial signal when close > open
        if bar.close > bar.open:
            return {
                "ts": bar.ts.isoformat(),
                "signal": "bullish_bar",
                "close": bar.close,
            }
        return None
