from edict.tv.analyzer import build_plan
from edict.tv.marketdata import Candle
from edict.tv.models import TradingViewSignal


def _candles_range(n: int, low: float, high: float):
    out = []
    for i in range(n):
        out.append(Candle(ts_ms=1000 * i, open=low, high=high, low=low, close=(low + high) / 2))
    return out


def test_build_plan_observe_until_breakout_long():
    candles = _candles_range(48, 100.0, 110.0)
    signal = TradingViewSignal(
        symbol="BTCUSDT",
        timeframe="1h",
        signal="tv_alert",
        side="long",
        price=109.0,
    )
    plan = build_plan(signal=signal, candles=candles)
    assert plan.decision == "观察"
    assert plan.direction == "做多"
    assert plan.entry is not None


def test_build_plan_execute_on_breakout_long():
    candles = _candles_range(48, 100.0, 110.0)
    signal = TradingViewSignal(
        symbol="BTCUSDT",
        timeframe="1h",
        signal="tv_alert",
        side="long",
        price=120.0,
    )
    plan = build_plan(signal=signal, candles=candles)
    assert plan.decision == "执行"
    assert plan.direction == "做多"
    assert plan.stop is not None
