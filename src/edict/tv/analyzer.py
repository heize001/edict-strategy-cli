from __future__ import annotations

from dataclasses import dataclass

from edict.tv.marketdata import Candle
from edict.tv.models import TradingViewSignal


@dataclass(frozen=True)
class TradePlan:
    decision: str  # 执行 / 观察 / 放弃
    direction: str  # 做多 / 做空 / -
    entry: float | None
    stop: float | None
    tp1: float | None
    tp2: float | None
    reason: str


def _pct(a: float, b: float) -> float:
    if b == 0:
        return 0.0
    return (a - b) / b * 100.0


def build_plan(
    *,
    signal: TradingViewSignal,
    candles: list[Candle],
    box_bars: int = 48,
    breakout_buffer_pct: float = 0.10,
) -> TradePlan:
    """Create a conservative plan from a TradingView signal + recent 1h candles.

    Philosophy:
    - Only act on 1h
    - Only follow (breakout/breakdown)
    - In range markets, only trade outside the box with a small buffer

    Notes:
    - This does not guarantee win-rate; it enforces strict quality gates.
    """

    if signal.timeframe.lower() not in {"1h", "60", "60m"}:
        return TradePlan("放弃", "-", None, None, None, None, "仅执行 1小时 信号")

    side = (signal.side or "").lower()
    if side not in {"long", "short"}:
        return TradePlan("观察", "-", None, None, None, None, "未提供明确方向 long/short")

    if len(candles) < box_bars:
        return TradePlan("观察", "-", None, None, None, None, "K线数据不足，暂停给明确指令")

    box = candles[-box_bars:]
    box_high = max(c.high for c in box)
    box_low = min(c.low for c in box)
    box_mid = (box_high + box_low) / 2.0

    price = signal.price or candles[-1].close

    buf = breakout_buffer_pct / 100.0
    long_trigger = box_high * (1 + buf)
    short_trigger = box_low * (1 - buf)

    # Risk model: structure stop at the opposite side of the box mid/edge.
    # TP: conservative multiples of box width.
    width = max(1e-9, box_high - box_low)

    if side == "long":
        # Only execute if price is already beyond trigger (implies close breakout)
        if price < long_trigger:
            reason = (
                f"多头追随仅在箱体上沿有效突破后执行。当前价未确认上破："
                f"触发>{long_trigger:.2f}（箱顶{box_high:.2f}+{breakout_buffer_pct:.2f}%缓冲）"
            )
            return TradePlan("观察", "做多", long_trigger, box_mid, None, None, reason)

        entry = price
        stop = box_mid
        tp1 = entry + 0.6 * width
        tp2 = entry + 1.0 * width
        reason = (
            f"1h 上破箱顶确认，执行追多；失效位=回落到箱体中枢附近。"
            f"（箱体高/低：{box_high:.2f}/{box_low:.2f}）"
        )
        return TradePlan("执行", "做多", entry, stop, tp1, tp2, reason)

    # short
    if price > short_trigger:
        reason = (
            f"空头追随仅在箱体下沿有效跌破后执行。当前价未确认下破："
            f"触发<{short_trigger:.2f}（箱底{box_low:.2f}-{breakout_buffer_pct:.2f}%缓冲）"
        )
        return TradePlan("观察", "做空", short_trigger, box_mid, None, None, reason)

    entry = price
    stop = box_mid
    tp1 = entry - 0.6 * width
    tp2 = entry - 1.0 * width
    reason = (
        f"1h 跌破箱底确认，执行追空；失效位=反弹回箱体中枢附近。"
        f"（箱体高/低：{box_high:.2f}/{box_low:.2f}）"
    )
    return TradePlan("执行", "做空", entry, stop, tp1, tp2, reason)
