from __future__ import annotations

import time
from dataclasses import dataclass

import httpx

HYPERLIQUID_INFO_URL = "https://api.hyperliquid.xyz/info"


@dataclass(frozen=True)
class Candle:
    ts_ms: int
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None


def _coin_from_symbol(symbol: str) -> str | None:
    s = symbol.upper().replace("/", "")
    if s.endswith("USDT"):
        s = s[: -4]
    if s.endswith("USD"):
        s = s[: -3]
    if s in {"BTC", "ETH"}:
        return s
    return None


async def fetch_hyperliquid_candles(
    *, symbol: str, interval: str = "1h", lookback_hours: int = 72
) -> list[Candle]:
    """Fetch candles from Hyperliquid public API.

    Works without API keys. Only supports common symbols like BTCUSDT/ETHUSDT.
    """

    coin = _coin_from_symbol(symbol)
    if coin is None:
        return []

    end_ms = int(time.time() * 1000)
    start_ms = end_ms - int(lookback_hours * 3600 * 1000)

    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": coin,
            "interval": interval,
            "startTime": start_ms,
            "endTime": end_ms,
        },
    }

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(HYPERLIQUID_INFO_URL, json=payload)
        resp.raise_for_status()
        data = resp.json()

    out: list[Candle] = []
    for row in data or []:
        try:
            out.append(
                Candle(
                    ts_ms=int(row.get("t")),
                    open=float(row.get("o")),
                    high=float(row.get("h")),
                    low=float(row.get("l")),
                    close=float(row.get("c")),
                    volume=float(row.get("v")) if row.get("v") is not None else None,
                )
            )
        except (TypeError, ValueError):
            continue

    out.sort(key=lambda c: c.ts_ms)
    return out
