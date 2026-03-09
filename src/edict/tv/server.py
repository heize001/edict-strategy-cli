from __future__ import annotations

import os

from fastapi import FastAPI, Header, HTTPException
from rich.console import Console

from edict.integrations.wecom import WeComClient
from edict.tv.models import TradingViewSignal

console = Console()


def create_app() -> FastAPI:
    app = FastAPI(title="edict-tv", version="0.1")

    secret = os.getenv("TV_WEBHOOK_SECRET")

    @app.get("/health")
    async def health():
        return {"ok": True}

    @app.post("/tv/webhook")
    async def tv_webhook(
        signal: TradingViewSignal,
        x_tv_secret: str | None = Header(default=None, alias="X-TV-SECRET"),
    ):
        if secret:
            if not x_tv_secret or x_tv_secret != secret:
                raise HTTPException(status_code=401, detail="invalid secret")

        # Notify WeCom
        try:
            wecom = WeComClient()
            await wecom.send_text(
                "\n".join(
                    [
                        "[TradingView Signal]",
                        f"symbol: {signal.symbol}",
                        f"timeframe: {signal.timeframe}",
                        f"exchange: {signal.exchange or '-'}",
                        f"signal: {signal.signal}",
                        f"side: {signal.side or '-'}",
                        f"price: {signal.price if signal.price is not None else '-'}",
                        f"ts: {signal.ts.isoformat() if signal.ts else '-'}",
                        f"note: {signal.note or '-'}",
                    ]
                )
            )
        except Exception as exc:  # noqa: BLE001
            console.print(f"WeCom send failed: {exc}")
            raise HTTPException(status_code=502, detail="wecom send failed") from exc

        return {"ok": True}

    return app
