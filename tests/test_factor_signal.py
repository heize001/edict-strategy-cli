from pathlib import Path

from edict.tv.factor import load_latest_factor_signal


def test_load_latest_factor_signal(tmp_path: Path, monkeypatch):
    sig_dir = tmp_path / "signals"
    sig_dir.mkdir()

    fp = sig_dir / "signal_20260309_10.csv"
    fp.write_text(
        "timestamp,iso_utc,symbol,side,weight,score,rank_xs\n"
        "1700000000000,2026-03-09 01:00:00,BTCUSDT,LONG,0.5,1.23,0.99\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("CAF_SIGNAL_DIR", str(sig_dir))
    s = load_latest_factor_signal("BTCUSDT")
    assert s is not None
    assert s.side == "LONG"
    assert s.score == 1.23
