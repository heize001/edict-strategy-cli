from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TradingViewSignal(BaseModel):
    """Normalized TradingView webhook payload.

    We intentionally keep it small and explicit.

    Recommended TV alert message JSON (example):
    {
      "symbol": "BTCUSDT",
      "timeframe": "1h",
      "exchange": "BINANCE",
      "signal": "breakout_long",
      "side": "long",
      "price": 66123.4,
      "ts": "{{timenow}}",
      "note": "optional"
    }
    """

    symbol: str = Field(..., examples=["BTCUSDT"])
    timeframe: str = Field("1h", examples=["1h", "15m"])
    exchange: str | None = Field(None, examples=["BINANCE", "OKX"])

    signal: str = Field(..., examples=["breakout_long"])
    side: str | None = Field(None, examples=["long", "short", "flat"])
    price: float | None = None

    ts: datetime | None = None
    note: str | None = None
