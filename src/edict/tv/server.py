from __future__ import annotations

import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Header, HTTPException, Query, Request
from rich.console import Console

from edict.integrations.wecom import WeComClient
from edict.tv.analyzer import build_plan
from edict.tv.factor import load_latest_factor_signal
from edict.tv.marketdata import fetch_hyperliquid_candles
from edict.tv.models import TradingViewSignal

console = Console()
JST = ZoneInfo("Asia/Tokyo")

# Default notify window (inclusive start, exclusive end) in JST
NOTIFY_START_HOUR = 9
NOTIFY_END_HOUR = 24

# De-dup window in seconds
DEDUP_TTL_SEC = 300

# In-memory dedup cache: key -> last_seen_epoch_sec
_DEDUP: dict[str, float] = {}


def _fmt_jst(ts: datetime | None) -> str:
    if ts is None:
        ts = datetime.now(tz=JST)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=JST)
    return ts.astimezone(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def _in_notify_window(now_jst: datetime) -> bool:
    # allow end=24 meaning 00:00 next day
    h = now_jst.hour
    if NOTIFY_END_HOUR == 24:
        return h >= NOTIFY_START_HOUR
    return NOTIFY_START_HOUR <= h < NOTIFY_END_HOUR


def _dedup_key(signal: TradingViewSignal) -> str:
    return "|".join(
        [
            (signal.symbol or "-").upper(),
            (signal.timeframe or "-").lower(),
            (signal.signal or "-").lower(),
            (signal.side or "-").lower(),
        ]
    )


def _dedup_should_drop(key: str, now_epoch: float) -> bool:
    # prune
    cutoff = now_epoch - DEDUP_TTL_SEC
    for k, t in list(_DEDUP.items()):
        if t < cutoff:
            _DEDUP.pop(k, None)

    last = _DEDUP.get(key)
    if last is not None and (now_epoch - last) < DEDUP_TTL_SEC:
        return True

    _DEDUP[key] = now_epoch
    return False


def create_app() -> FastAPI:
    app = FastAPI(title="edict-tv", version="0.1")

    secret = os.getenv("TV_WEBHOOK_SECRET")

    @app.get("/health")
    async def health():
        return {"ok": True}

    @app.post("/tv/webhook")
    async def tv_webhook(
        request: Request,
        x_tv_secret: str | None = Header(default=None, alias="X-TV-SECRET"),
        secret_qs: str | None = Query(default=None, alias="secret"),
    ):
        """Receive TradingView webhook.

        TradingView's webhook UI typically doesn't support custom headers.
        So we accept the secret either via header `X-TV-SECRET` or query string
        `?secret=<value>`.
        """

        if secret:
            provided = x_tv_secret or secret_qs
            if not provided or provided != secret:
                raise HTTPException(status_code=401, detail="invalid secret")

        raw = (await request.body()).decode("utf-8", errors="replace").strip()

        payload: dict | None = None
        if raw:
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload = None

        if payload is None:
            # Fallback: treat as plain-text message
            signal = TradingViewSignal(
                symbol="UNKNOWN",
                timeframe="unknown",
                exchange=None,
                signal="tv_raw",
                side=None,
                price=None,
                ts=None,
                note=raw,
            )
        else:
            try:
                signal = TradingViewSignal.model_validate(payload)
            except Exception as exc:  # noqa: BLE001
                raise HTTPException(status_code=422, detail=f"invalid payload: {exc}") from exc

        # Decide notify (window + dedup)
        now_jst = datetime.now(tz=JST)
        if not _in_notify_window(now_jst):
            return {"ok": True, "skipped": "outside_notify_window"}

        key = _dedup_key(signal)
        if _dedup_should_drop(key, now_jst.timestamp()):
            return {"ok": True, "skipped": "dedup"}

        # Analysis -> instruction
        candles = await fetch_hyperliquid_candles(
            symbol=signal.symbol,
            interval="1h",
            lookback_hours=96,
        )
        plan = build_plan(signal=signal, candles=candles)

        factor = load_latest_factor_signal(signal.symbol)
        factor_lines: list[str] = []
        if factor is None:
            factor_lines = ["因子：未找到本地因子信号（CAF_SIGNAL_DIR）"]
        else:
            factor_side_cn = {"LONG": "偏多", "SHORT": "偏空"}.get(
                (factor.side or "").upper(),
                factor.side or "-",
            )
            score_txt = factor.score if factor.score is not None else "-"
            rank_txt = factor.rank_xs if factor.rank_xs is not None else "-"
            factor_lines = [
                f"因子：{factor_side_cn}｜score={score_txt}｜rank={rank_txt}",
                f"因子来源：{factor.source_file}",
            ]

        # Notify WeCom
        try:
            wecom = WeComClient()
            side_cn = {"long": "做多", "short": "做空", "flat": "观望"}.get(
                (signal.side or "").lower(),
                signal.side or "-",
            )
            price_txt = f"{signal.price:.2f}" if isinstance(signal.price, (int, float)) else "-"

            def fmt(v: float | None) -> str:
                return f"{v:.2f}" if isinstance(v, (int, float)) else "-"

            await wecom.send_text(
                "\n".join(
                    [
                        "【TradingView 信号→分析→指令】",
                        f"品种：{signal.symbol}（{signal.exchange or '-'}）",
                        f"周期：{signal.timeframe}",
                        f"原始信号：{signal.signal}｜{side_cn}",
                        f"触发价：{price_txt}",
                        f"时间：{_fmt_jst(signal.ts)}",
                        *factor_lines,
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
                        "提示：不满足条件就不做；不追插针。",
                    ]
                )
            )
        except Exception as exc:  # noqa: BLE001
            console.print(f"WeCom send failed: {exc}")
            raise HTTPException(status_code=502, detail="wecom send failed") from exc

        return {"ok": True, "decision": plan.decision}

    return app
