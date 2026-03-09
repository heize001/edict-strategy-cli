from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
import yaml
from rich.console import Console
from rich.table import Table

from edict.core.engine import Engine
from edict.core.loader import load_strategy_class
from edict.core.models import Bar
from edict.core.strategy import StrategyContext

app = typer.Typer(add_completion=False, no_args_is_help=True)
console = Console()


def _load_config(path: Path) -> dict:
    if not path.exists():
        raise typer.BadParameter(f"Config not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _load_bars_from_jsonl(path: Path) -> list[Bar]:
    bars: list[Bar] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            bars.append(Bar.model_validate_json(line))
    return bars


@app.command()
def strategies() -> None:
    """List built-in strategies."""
    table = Table(title="Built-in strategies")
    table.add_column("spec")
    table.add_column("name")
    from edict.strategies.demo import DemoStrategy

    items = [
        ("edict.strategies.demo:DemoStrategy", DemoStrategy.name),
    ]
    for spec, name in items:
        table.add_row(spec, name)
    console.print(table)


@app.command()
def run(
    strategy: str = typer.Option(..., "--strategy", help="Strategy spec: module:ClassName"),
    config: Path = typer.Option(..., "--config", exists=False, help="YAML config path"),
    bars: Optional[Path] = typer.Option(None, "--bars", help="Optional JSONL bars file"),
) -> None:
    """Run a strategy."""

    cfg = _load_config(config)
    symbol = str(cfg.get("symbol", "BTCUSDT"))
    timeframe = str(cfg.get("timeframe", "1h"))

    StrategyCls = load_strategy_class(strategy)
    ctx = StrategyContext(config=cfg, symbol=symbol, timeframe=timeframe)
    strat = StrategyCls(ctx)

    engine = Engine(console=console)

    # Demo bars when none provided
    if bars is None:
        demo = [
            Bar.model_validate(
                {
                    "ts": "2026-03-09T00:00:00Z",
                    "open": 66000,
                    "high": 66200,
                    "low": 65900,
                    "close": 66150,
                    "volume": 123.4,
                }
            ),
            Bar.model_validate(
                {
                    "ts": "2026-03-09T01:00:00Z",
                    "open": 66150,
                    "high": 66220,
                    "low": 65850,
                    "close": 65950,
                    "volume": 234.5,
                }
            ),
        ]
        bars_iter = demo
    else:
        bars_iter = _load_bars_from_jsonl(bars)

    signals = engine.run(strat, bars_iter)
    console.print(json.dumps({"signals": signals}, ensure_ascii=False, indent=2))
