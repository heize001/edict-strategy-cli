from pathlib import Path

from typer.testing import CliRunner

from edict.cli.app import app


def test_run_reads_strategy_from_config(tmp_path: Path):
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text(
        "symbol: BTCUSDT\n"
        "timeframe: 1h\n"
        "strategy: edict.strategies.demo:DemoStrategy\n",
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(app, ["run", "--config", str(cfg)])
    assert result.exit_code == 0
    assert "signals" in result.stdout
