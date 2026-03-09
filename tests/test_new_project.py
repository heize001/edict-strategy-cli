from pathlib import Path

from typer.testing import CliRunner

from edict.cli.app import app


def test_new_project_generates_layout(tmp_path: Path):
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "new-project",
            "my-proj",
            "--out",
            str(tmp_path),
            "--strategy",
            "mean-reversion",
        ],
    )
    assert result.exit_code == 0

    root = tmp_path / "my-proj"
    assert (root / "pyproject.toml").exists()
    assert (root / "src" / "strategies" / "mean_reversion.py").exists()
    assert (root / "configs" / "mean_reversion.yaml").exists()
    assert (root / "tests" / "test_mean_reversion.py").exists()
    assert (root / ".github" / "workflows" / "ci.yml").exists()
