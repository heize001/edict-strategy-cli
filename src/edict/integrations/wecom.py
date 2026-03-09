from __future__ import annotations

import os

import httpx


class WeComClient:
    def __init__(self, webhook_url: str | None = None):
        self.webhook_url = webhook_url or os.getenv("WECOM_WEBHOOK_URL")
        if not self.webhook_url:
            raise ValueError("Missing WeCom webhook url. Set WECOM_WEBHOOK_URL")

    async def send_text(self, content: str) -> None:
        payload = {
            "msgtype": "text",
            "text": {
                "content": content,
            },
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(self.webhook_url, json=payload)
            resp.raise_for_status()
