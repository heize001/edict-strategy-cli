from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FactorSignal:
    timestamp: int | None
    iso_utc: str | None
    symbol: str
    side: str | None  # LONG/SHORT
    weight: float | None
    score: float | None
    rank_xs: float | None
    source_file: str


def _default_signal_dir() -> Path:
    # CAF default
    return Path(os.getenv("CAF_SIGNAL_DIR", "/Volumes/CAF/CryptoAlphaFactory/signals/daily"))


def load_latest_factor_signal(symbol: str) -> FactorSignal | None:
    """Load the latest CAF factor signal for a given symbol.

    Expects files like: signal_YYYYMMDD_HH.csv under CAF_SIGNAL_DIR.
    """

    sym = symbol.strip().upper()
    sig_dir = _default_signal_dir()
    if not sig_dir.exists():
        return None

    files = sorted(sig_dir.glob("signal_*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return None

    # Scan a few recent files (avoid heavy IO)
    for fp in files[:24]:
        try:
            with fp.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if (row.get("symbol") or "").strip().upper() != sym:
                        continue

                    def fnum(v: str | None) -> float | None:
                        if v is None or str(v).strip() == "":
                            return None
                        try:
                            return float(v)
                        except ValueError:
                            return None

                    def inum(v: str | None) -> int | None:
                        if v is None or str(v).strip() == "":
                            return None
                        try:
                            return int(float(v))
                        except ValueError:
                            return None

                    return FactorSignal(
                        timestamp=inum(row.get("timestamp")),
                        iso_utc=(row.get("iso_utc") or None),
                        symbol=sym,
                        side=(row.get("side") or None),
                        weight=fnum(row.get("weight")),
                        score=fnum(row.get("score")),
                        rank_xs=fnum(row.get("rank_xs")),
                        source_file=str(fp),
                    )
        except Exception:
            continue

    return None
