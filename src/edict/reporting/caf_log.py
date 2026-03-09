from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class CafDecisionLog:
    created_at_utc: str
    caf_timestamp_ms: int | None
    symbol: str

    factor_side: str | None
    factor_score: float | None
    factor_rank_xs: float | None
    factor_source_file: str

    decision: str  # 执行 / 观察 / 放弃
    direction: str  # 做多 / 做空 / -
    entry: float | None
    stop: float | None
    tp1: float | None
    tp2: float | None
    reason: str


def _day_path(root: Path, dt_utc: datetime) -> Path:
    return root / f"{dt_utc.strftime('%Y-%m-%d')}.jsonl"


def append_jsonl(root: Path, item: CafDecisionLog) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    dt = datetime.utcnow()
    fp = _day_path(root, dt)
    with fp.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(item), ensure_ascii=False) + "\n")
    return fp
