"""Tests for Open Research Pipeline."""

import pytest
import tempfile
from pathlib import Path

from open_research_pipeline.core.runner import ExperimentRunner, ExperimentConfig
import zipfile


class TestExperimentConfig:
    """Test ExperimentConfig dataclass."""

    def test_experiment_config_creation(self):
        """Test creating an experiment configuration."""
        config = ExperimentConfig(
            name="test_experiment",
            description="A test experiment",
            training_script="python train.py",
            training_config={"lr": 0.001},
            deliverables=[{"type": "model", "path": "output/model"}]
        )

        assert config.name == "test_experiment"
        assert config.description == "A test experiment"
        assert config.training_script == "python train.py"
        assert config.training_config == {"lr": 0.001}
        assert config.deliverables == [{"type": "model", "path": "output/model"}]


class TestExperimentRunner:
    """Test ExperimentRunner class."""

    def test_runner_initialization(self):
        """Test that runner creates necessary directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            runner = ExperimentRunner(temp_dir)

            assert (Path(temp_dir) / "queue").exists()
            assert (Path(temp_dir) / "completed").exists()
            assert (Path(temp_dir) / "failed").exists()
            assert (Path(temp_dir) / "artifacts").exists()

    def test_load_experiment_config(self):
        """Test loading experiment config from YAML."""
        config_yaml = """
experiment:
  name: "test_experiment"
  description: "A test experiment"
training:
  script: "python train.py"
  config:
    learning_rate: 0.001
deliverables:
  - type: "model"
    path: "output/model"
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_yaml)
            f.flush()

            runner = ExperimentRunner()
            config = runner.load_experiment_config(f.name)

            assert config.name == "test_experiment"
            assert config.training_script == "python train.py"
            assert config.training_config["learning_rate"] == 0.001

        Path(f.name).unlink()  # cleanup

    def test_artifacts_include_training_logs(self):
        """Simulate a training script that writes to stdout and stderr and ensure logs are zipped."""
        # Create a tiny script that prints to stdout and stderr
        script_content = """import sys
print('TRAINING STDOUT LINE')
print('TRAINING STDERR LINE', file=sys.stderr)
"""

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            script_path = temp_path / "fake_train.py"
            script_path.write_text(script_content)

            # Use a config that runs the script
            config = ExperimentConfig(
                name="log_test",
                training_script=["python", str(script_path)],
                training_config={},
                deliverables=[]
            )

            runner = ExperimentRunner(temp_dir)

            result = runner.run_experiment(config)

            # Artifacts zip path should be recorded on the result
            assert result.artifacts_path is not None
            zip_path = Path(result.artifacts_path)
            assert zip_path.exists()
            with zipfile.ZipFile(zip_path, 'r') as z:
                namelist = z.namelist()
                assert 'training_stdout.txt' in namelist
                assert 'training_stderr.txt' in namelist

    def test_failing_run_preserves_logs(self):
        """Simulate a training script that exits non-zero and ensure logs are preserved and status is failed."""
        # Create a tiny script that writes to stderr and exits with code 2
        script_content = """import sys
print('ALIVE STDOUT')
print('ALIVE STDERR', file=sys.stderr)
sys.exit(2)
"""

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            script_path = temp_path / "bad_train.py"
            script_path.write_text(script_content)

            config = ExperimentConfig(
                name="fail_test",
                training_script=["python", str(script_path)],
                training_config={},
                deliverables=[]
            )

            runner = ExperimentRunner(temp_dir)

            result = runner.run_experiment(config)

            assert result.status == 'failed'
            # artifacts_path should be set to the zip (if packaging succeeded)
            if result.artifacts_path:
                zip_path = Path(result.artifacts_path)
                assert zip_path.exists()
                with zipfile.ZipFile(zip_path, 'r') as z:
                    namelist = z.namelist()
                    # logs should be inside the zip
                    assert 'training_stdout.txt' in namelist or 'training_stderr.txt' in namelist
            # training_*_path fields should reference the zip-qualified paths when available
            if result.training_stderr_path:
                assert '::training_stderr.txt' in result.training_stderr_path
            if result.training_stdout_path:
                assert '::training_stdout.txt' in result.training_stdout_path