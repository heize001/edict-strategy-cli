from __future__ import annotations

import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Header, HTTPException, Query, Request
from rich.console import Console

from edict.integrations.wecom import WeComClient
from edict.tv.models import TradingViewSignal

console = Console()
JST = ZoneInfo("Asia/Tokyo")


def _fmt_jst(ts: datetime | None) -> str:
    if ts is None:
        ts = datetime.now(tz=JST)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=JST)
    return ts.astimezone(JST).strftime("%Y-%m-%d %H:%M:%S JST")


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

        # Notify WeCom
        try:
            wecom = WeComClient()
            side_cn = {"long": "做多", "short": "做空", "flat": "观望"}.get(
                (signal.side or "").lower(),
                signal.side or "-",
            )
            price_txt = f"{signal.price:.2f}" if isinstance(signal.price, (int, float)) else "-"

            await wecom.send_text(
                "\n".join(
                    [
                        "【TradingView 信号】",
                        f"品种：{signal.symbol}",
                        f"周期：{signal.timeframe}",
                        f"交易所：{signal.exchange or '-'}",
                        f"信号：{signal.signal}",
                        f"方向：{side_cn}",
                        f"价格：{price_txt}",
                        f"时间：{_fmt_jst(signal.ts)}",
                        f"备注：{signal.note or '-'}",
                    ]
                )
            )
        except Exception as exc:  # noqa: BLE001
            console.print(f"WeCom send failed: {exc}")
            raise HTTPException(status_code=502, detail="wecom send failed") from exc

        return {"ok": True}

    return app
