from __future__ import annotations

import asyncio
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from edict.integrations.wecom import WeComClient
from edict.reporting.caf_backtest import eval_last_24h

JST = ZoneInfo("Asia/Tokyo")


def _pct(n: int, d: int) -> str:
    if d <= 0:
        return "-"
    return f"{(n / d) * 100:.1f}%"


async def main() -> None:
    log_root = Path(os.getenv("EDICT_CAF_LOG_DIR", "data/caf_logs"))
    now_utc = datetime.now(tz=timezone.utc)
    res = await eval_last_24h(log_root=log_root, now_utc=now_utc)

    # core counts
    counts = Counter(r.status for r in res)
    win = counts.get("win", 0)
    loss = counts.get("loss", 0)
    scored = win + loss

    # decision breakdown
    decision_counts = Counter(r.decision for r in res)

    # top loss notes (rough)
    loss_notes = [r.note for r in res if r.status == "loss"]
    top_loss = Counter(loss_notes).most_common(3)

    # timeframe label
    now_jst = now_utc.astimezone(JST)
    title = f"【CAF 每日复盘】{now_jst.strftime('%Y-%m-%d')} 09:00 JST"

    lines = [
        title,
        f"统计区间：过去24小时（截至 {now_jst.strftime('%Y-%m-%d %H:%M')} JST）",
        "---",
        f"胜率：{_pct(win, scored)}（胜{win}/负{loss}）",
        (
            "未触发："
            f"{counts.get('not_triggered', 0)}｜超时：{counts.get('timeout', 0)}"
            f"｜跳过：{counts.get('skipped', 0)}"
        ),
        "指令分布：" + "，".join(f"{k}:{v}" for k, v in decision_counts.items() if k),
    ]

    if top_loss:
        lines.append("---")
        lines.append("亏损常见原因Top3（粗略）：")
        for i, (k, v) in enumerate(top_loss, start=1):
            lines.append(f"{i}) {k} ×{v}")

    lines.append("---")
    lines.append("今日优化方向：继续提高共振过滤（因子方向×结构确认），宁可少做。")

    wecom = WeComClient()
    await wecom.send_text("\n".join(lines))


if __name__ == "__main__":
    asyncio.run(main())
