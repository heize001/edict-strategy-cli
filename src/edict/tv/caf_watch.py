from __future__ import annotations

import asyncio
import os
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from rich.console import Console

from edict.integrations.wecom import WeComClient
from edict.reporting.caf_log import CafDecisionLog, append_jsonl
from edict.tv.analyzer import build_plan
from edict.tv.factor import FactorSignal, load_factor_signals_from_file
from edict.tv.marketdata import fetch_hyperliquid_candles
from edict.tv.models import TradingViewSignal

console = Console()
JST = ZoneInfo("Asia/Tokyo")

# Notify window (JST)
NOTIFY_START_HOUR = 9
NOTIFY_END_HOUR = 24

# De-dup window
DEDUP_TTL_SEC = 300
_DEDUP: dict[str, float] = {}


def _in_notify_window(now_jst: datetime) -> bool:
    if NOTIFY_END_HOUR == 24:
        return now_jst.hour >= NOTIFY_START_HOUR
    return NOTIFY_START_HOUR <= now_jst.hour < NOTIFY_END_HOUR


def _dedup_should_drop(key: str, now_epoch: float) -> bool:
    cutoff = now_epoch - DEDUP_TTL_SEC
    for k, t in list(_DEDUP.items()):
        if t < cutoff:
            _DEDUP.pop(k, None)

    last = _DEDUP.get(key)
    if last is not None and (now_epoch - last) < DEDUP_TTL_SEC:
        return True

    _DEDUP[key] = now_epoch
    return False


def _caf_signal_dir() -> Path:
    return Path(os.getenv("CAF_SIGNAL_DIR", "/Volumes/CAF/CryptoAlphaFactory/signals/daily"))


def _latest_signal_file() -> Path | None:
    sig_dir = _caf_signal_dir()
    if not sig_dir.exists():
        return None
    files = sorted(sig_dir.glob("signal_*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def _side_to_tv(side: str | None) -> str | None:
    s = (side or "").upper()
    if s == "LONG":
        return "long"
    if s == "SHORT":
        return "short"
    return None


def _factor_side_cn(side: str | None) -> str:
    return {"LONG": "偏多", "SHORT": "偏空"}.get((side or "").upper(), side or "-")


async def _analyze_one(fs: FactorSignal) -> tuple[FactorSignal, TradingViewSignal, str]:
    """Return (factor, tv_signal, decision)."""

    tv_side = _side_to_tv(fs.side)
    candles = await fetch_hyperliquid_candles(symbol=fs.symbol, interval="1h", lookback_hours=96)
    price = candles[-1].close if candles else None

    tv = TradingViewSignal(
        symbol=fs.symbol,
        timeframe="1h",
        exchange="CAF",
        signal="caf_factor",
        side=tv_side,
        price=price,
        ts=None,
        note=f"factor={_factor_side_cn(fs.side)} score={fs.score} rank={fs.rank_xs}",
    )

    plan = build_plan(signal=tv, candles=candles)
    return fs, tv, plan.decision


async def caf_watch(
    *,
    include_btc_eth: bool = True,
    include_file_rows: bool = True,
    poll_sec: int = 15,
) -> None:
    """Watch CAF factor signals and push analysis to WeCom."""

    wecom = WeComClient()
    last_sig_id: tuple[str, int | None] | None = None

    console.print(
        f"[caf-watch] watching {str(_caf_signal_dir())}"
        f" poll={poll_sec}s btc/eth={include_btc_eth} rows={include_file_rows}"
    )

    while True:
        now_jst = datetime.now(tz=JST)
        if not _in_notify_window(now_jst):
            await asyncio.sleep(poll_sec)
            continue

        fp = _latest_signal_file()
        if fp is None:
            await asyncio.sleep(poll_sec)
            continue

        rows = load_factor_signals_from_file(fp)
        data_ts = None
        ts_vals = [r.timestamp for r in rows if r.timestamp is not None]
        if ts_vals:
            data_ts = max(ts_vals)

        sig_id = (str(fp), data_ts)
        if last_sig_id == sig_id:
            await asyncio.sleep(poll_sec)
            continue

        # New signal detected (file path + data timestamp)
        last_sig_id = sig_id

        # Build targets
        targets: dict[str, FactorSignal] = {}

        if include_file_rows:
            for r in rows:
                targets[r.symbol] = r

        if include_btc_eth:
            for sym in ("BTCUSDT", "ETHUSDT"):
                for r in rows:
                    if r.symbol == sym:
                        targets[sym] = r

        if not targets:
            await asyncio.sleep(poll_sec)
            continue

        console.print(f"[caf-watch] new signal: file={fp.name} data_ts={data_ts}")

        # Analyze and send
        for sym, fs in targets.items():
            key = f"caf|{sym}|{fs.side}|{fs.timestamp or ''}"
            if _dedup_should_drop(key, time.time()):
                continue

            candles = await fetch_hyperliquid_candles(
                symbol=fs.symbol,
                interval="1h",
                lookback_hours=96,
            )
            price = candles[-1].close if candles else None

            tv_side = _side_to_tv(fs.side)
            tv = TradingViewSignal(
                symbol=fs.symbol,
                timeframe="1h",
                exchange="CAF",
                signal="caf_factor",
                side=tv_side,
                price=price,
                ts=None,
                note=None,
            )
            plan = build_plan(signal=tv, candles=candles)

            price_txt = f"{price:.2f}" if isinstance(price, (int, float)) else "-"
            score_txt = fs.score if fs.score is not None else "-"
            rank_txt = fs.rank_xs if fs.rank_xs is not None else "-"
            factor_line = f"因子：{_factor_side_cn(fs.side)}｜score={score_txt}｜rank={rank_txt}"

            def fmt(v: float | None) -> str:
                return f"{v:.2f}" if isinstance(v, (int, float)) else "-"

            msg = "\n".join(
                [
                    "【CAF 因子信号→分析→指令】",
                    f"品种：{fs.symbol}",
                    f"时间：{now_jst.strftime('%Y-%m-%d %H:%M:%S JST')}",
                    factor_line,
                    f"来源：{fs.source_file}",
                    f"参考现价：{price_txt}",
                    "---",
                    f"结论：{plan.decision}",
                    f"方向：{plan.direction}",
                    f"入场：{fmt(plan.entry)}",
                    f"止损：{fmt(plan.stop)}",
                    f"止盈1：{fmt(plan.tp1)}",
                    f"止盈2：{fmt(plan.tp2)}",
                    f"理由：{plan.reason}",
                    "---",
                    "风控：逐仓；单笔最大亏损建议≤0.2%权益（50x建议更小）。",
                ]
            )

            await wecom.send_text(msg)

            # Persist for daily backtest/recap
            log_root = Path(os.getenv("EDICT_CAF_LOG_DIR", "data/caf_logs"))
            append_jsonl(
                log_root,
                CafDecisionLog(
                    created_at_utc=datetime.utcnow().isoformat() + "Z",
                    caf_timestamp_ms=fs.timestamp,
                    symbol=fs.symbol,
                    factor_side=fs.side,
                    factor_score=fs.score,
                    factor_rank_xs=fs.rank_xs,
                    factor_source_file=fs.source_file,
                    decision=plan.decision,
                    direction=plan.direction,
                    entry=plan.entry,
                    stop=plan.stop,
                    tp1=plan.tp1,
                    tp2=plan.tp2,
                    reason=plan.reason,
                ),
            )

        await asyncio.sleep(poll_sec)
