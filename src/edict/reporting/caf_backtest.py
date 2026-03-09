from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from edict.tv.marketdata import fetch_hyperliquid_candles


@dataclass(frozen=True)
class EvalResult:
    key: str
    symbol: str
    decision: str
    direction: str
    entry: float | None
    stop: float | None
    tp1: float | None
    created_at_utc: datetime

    status: str  # win / loss / not_triggered / timeout / skipped
    note: str


def _parse_dt(s: str) -> datetime:
    # expects isoformat + optional Z
    s = s.rstrip("Z")
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _load_jsonl(fp: Path) -> list[dict]:
    if not fp.exists():
        return []
    out: list[dict] = []
    with fp.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


async def eval_last_24h(
    *,
    log_root: Path,
    now_utc: datetime | None = None,
    trigger_valid_hours: int = 12,
    outcome_window_hours: int = 24,
) -> list[EvalResult]:
    now_utc = now_utc or datetime.now(tz=timezone.utc)
    start_utc = now_utc - timedelta(hours=24)

    # read yesterday+today (cheap)
    fps = {
        log_root / f"{start_utc.strftime('%Y-%m-%d')}.jsonl",
        log_root / f"{now_utc.strftime('%Y-%m-%d')}.jsonl",
    }

    items: list[dict] = []
    for fp in fps:
        items.extend(_load_jsonl(fp))

    results: list[EvalResult] = []

    for it in items:
        try:
            created = _parse_dt(str(it.get("created_at_utc")))
        except Exception:
            continue
        if created < start_utc or created > now_utc:
            continue

        decision = str(it.get("decision", ""))
        direction = str(it.get("direction", ""))
        symbol = str(it.get("symbol", ""))
        entry = it.get("entry")
        stop = it.get("stop")
        tp1 = it.get("tp1")

        try:
            entry_f = float(entry) if entry is not None else None
            stop_f = float(stop) if stop is not None else None
            tp1_f = float(tp1) if tp1 is not None else None
        except (TypeError, ValueError):
            entry_f = stop_f = tp1_f = None

        key = f"{created.isoformat()}|{symbol}|{direction}|{decision}"

        # We only score trades that provide entry/stop/tp1
        if decision not in {"执行", "观察"} or entry_f is None or stop_f is None or tp1_f is None:
            results.append(
                EvalResult(
                    key=key,
                    symbol=symbol,
                    decision=decision,
                    direction=direction,
                    entry=entry_f,
                    stop=stop_f,
                    tp1=tp1_f,
                    created_at_utc=created,
                    status="skipped",
                    note="no-scoring-fields",
                )
            )
            continue

        # Fetch candles around the decision time
        # We fetch 96h and then slice; keep it simple.
        candles = await fetch_hyperliquid_candles(symbol=symbol, interval="1h", lookback_hours=120)
        if not candles:
            results.append(
                EvalResult(
                    key=key,
                    symbol=symbol,
                    decision=decision,
                    direction=direction,
                    entry=entry_f,
                    stop=stop_f,
                    tp1=tp1_f,
                    created_at_utc=created,
                    status="timeout",
                    note="no-candles",
                )
            )
            continue

        created_ms = int(created.timestamp() * 1000)
        trigger_deadline_ms = created_ms + trigger_valid_hours * 3600 * 1000
        outcome_deadline_ms = created_ms + outcome_window_hours * 3600 * 1000

        # Find trigger candle
        triggered_at_ms: int | None = None
        for c in candles:
            if c.ts_ms < created_ms:
                continue
            if c.ts_ms > trigger_deadline_ms:
                break

            if direction == "做多":
                if c.high >= entry_f:
                    triggered_at_ms = c.ts_ms
                    break
            elif direction == "做空":
                if c.low <= entry_f:
                    triggered_at_ms = c.ts_ms
                    break

        if triggered_at_ms is None:
            results.append(
                EvalResult(
                    key=key,
                    symbol=symbol,
                    decision=decision,
                    direction=direction,
                    entry=entry_f,
                    stop=stop_f,
                    tp1=tp1_f,
                    created_at_utc=created,
                    status="not_triggered",
                    note=f"not triggered within {trigger_valid_hours}h",
                )
            )
            continue

        # After trigger, check which hit first: tp1 vs stop
        status = "timeout"
        trig_dt = datetime.fromtimestamp(triggered_at_ms / 1000, tz=timezone.utc).isoformat()
        note = f"triggered at {trig_dt}"

        for c in candles:
            if c.ts_ms < triggered_at_ms:
                continue
            if c.ts_ms > outcome_deadline_ms:
                break

            if direction == "做多":
                hit_tp = c.high >= tp1_f
                hit_sl = c.low <= stop_f
            else:
                hit_tp = c.low <= tp1_f
                hit_sl = c.high >= stop_f

            if hit_tp and hit_sl:
                # ambiguous within one candle; be conservative
                status = "loss"
                note += " | both hit same candle -> conservative loss"
                break
            if hit_sl:
                status = "loss"
                note += " | SL first"
                break
            if hit_tp:
                status = "win"
                note += " | TP1 first"
                break

        results.append(
            EvalResult(
                key=key,
                symbol=symbol,
                decision=decision,
                direction=direction,
                entry=entry_f,
                stop=stop_f,
                tp1=tp1_f,
                created_at_utc=created,
                status=status,
                note=note,
            )
        )

    return results
