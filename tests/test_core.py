"""Tests for Open Research Pipeline."""

import pytest
import tempfile
from pathlib import Path

from open_research_pipeline.core.runner import ExperimentRunner, ExperimentConfig


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