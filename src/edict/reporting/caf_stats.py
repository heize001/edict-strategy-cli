from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WinLoss:
    win: int
    loss: int

    @property
    def n(self) -> int:
        return self.win + self.loss

    @property
    def winrate(self) -> float | None:
        if self.n <= 0:
            return None
        return self.win / self.n


@dataclass(frozen=True)
class CafStats:
    long: WinLoss
    short: WinLoss


def load_stats(path: Path) -> CafStats | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        long = data.get("long", {})
        short = data.get("short", {})
        return CafStats(
            long=WinLoss(win=int(long.get("win", 0)), loss=int(long.get("loss", 0))),
            short=WinLoss(win=int(short.get("win", 0)), loss=int(short.get("loss", 0))),
        )
    except Exception:
        return None


def save_stats(path: Path, stats: CafStats) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "long": {"win": stats.long.win, "loss": stats.long.loss},
        "short": {"win": stats.short.win, "loss": stats.short.loss},
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
