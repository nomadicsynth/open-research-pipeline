import json
import sys
from pathlib import Path

import pytest

from open_research_pipeline.core.runner import ExperimentRunner, ExperimentConfig


def make_writer_script(dir_path: Path, filename: str, contents: dict) -> str:
    """Create a tiny python script that writes the given JSON to `output/metrics.json`.

    Returns the script path as string.
    """
    script_path = dir_path / filename
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_code = (
        "import json, pathlib\n"
        "p=pathlib.Path('output')\n"
        "p.mkdir(parents=True, exist_ok=True)\n"
        f"json.dump({json.dumps(contents)}, open(p / 'metrics.json', 'w'))\n"
    )
    script_path.write_text(script_code, encoding='utf-8')
    script_path.chmod(0o755)
    return str(script_path)


def test_contains_keys_via_run_experiment_missing_key(tmp_path: Path):
    runner = ExperimentRunner(base_dir=str(tmp_path / "experiments"))

    work = tmp_path / "run_missing"
    work.mkdir()
    # Script writes only learning_rate, missing 'accuracy'
    script = make_writer_script(work, "write_metrics_missing.py", {"learning_rate": 0.01})

    config = ExperimentConfig(
        name="e2e_missing_key",
        description="writes metrics missing accuracy",
        training_script=[sys.executable, script],
        training_config={},
        deliverables=[
            {
                "type": "metrics",
                "path": "output/metrics.json",
                "validation": "contains_keys",
                "required_keys": ["accuracy", "learning_rate"],
            }
        ],
    )

    result = runner.run_experiment(config)

    assert result.status == "completed"
    ds = result.deliverables_status["metrics"]
    assert ds["validated"] is False
    assert "accuracy" in ds.get("missing_keys", [])


def test_contains_keys_via_run_experiment_all_present(tmp_path: Path):
    runner = ExperimentRunner(base_dir=str(tmp_path / "experiments"))

    work = tmp_path / "run_all"
    work.mkdir()
    # Script writes both keys
    script = make_writer_script(work, "write_metrics_ok.py", {"accuracy": 0.9, "learning_rate": 0.01})

    config = ExperimentConfig(
        name="e2e_all_keys",
        description="writes metrics with required keys",
        training_script=[sys.executable, script],
        training_config={},
        deliverables=[
            {
                "type": "metrics",
                "path": "output/metrics.json",
                "validation": "contains_keys",
                "required_keys": ["accuracy", "learning_rate"],
            }
        ],
    )

    result = runner.run_experiment(config)

    assert result.status == "completed"
    ds = result.deliverables_status["metrics"]
    assert ds["validated"] is True
    assert ds.get("missing_keys", []) == []
