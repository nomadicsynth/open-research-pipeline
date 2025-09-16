"""Core experiment runner functionality."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class ExperimentConfig:
    """Configuration for a single experiment."""

    name: str
    description: str = ""
    training_script: str = ""
    training_config: Dict[str, Any] = None
    deliverables: List[Dict[str, Any]] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.training_config is None:
            self.training_config = {}
        if self.deliverables is None:
            self.deliverables = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ExperimentResult:
    """Result of running an experiment."""

    experiment_id: str
    status: str  # "completed", "failed", "running"
    start_time: datetime
    end_time: Optional[datetime] = None
    deliverables_status: Dict[str, Any] = None
    error_message: Optional[str] = None
    artifacts_path: Optional[str] = None

    def __post_init__(self):
        if self.deliverables_status is None:
            self.deliverables_status = {}


class ExperimentRunner:
    """Core experiment runner that orchestrates training and validation."""

    def __init__(self, base_dir: str = "experiments"):
        self.base_dir = Path(base_dir)
        self.queue_dir = self.base_dir / "queue"
        self.completed_dir = self.base_dir / "completed"
        self.failed_dir = self.base_dir / "failed"
        self.artifacts_dir = self.base_dir / "artifacts"

        # Create directories
        for dir_path in [self.queue_dir, self.completed_dir, self.failed_dir, self.artifacts_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

    def load_experiment_config(self, config_path: str) -> ExperimentConfig:
        """Load experiment configuration from YAML file."""
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)

        return ExperimentConfig(
            name=data.get('experiment', {}).get('name', 'unnamed'),
            description=data.get('experiment', {}).get('description', ''),
            training_script=data.get('training', {}).get('script', ''),
            training_config=data.get('training', {}).get('config', {}),
            deliverables=data.get('deliverables', []),
            metadata=data.get('metadata', {})
        )

    def run_experiment(self, config: ExperimentConfig) -> ExperimentResult:
        """Run a single experiment."""
        experiment_id = f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.now()

        print(f"Starting experiment: {experiment_id}")
        print(f"Name: {config.name}")
        print(f"Description: {config.description}")

        try:
            # Create temporary directory for this experiment
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Run the training script
                self._run_training_script(config, temp_path)

                # Validate deliverables
                deliverables_status = self._validate_deliverables(config.deliverables, temp_path)

                # Package artifacts
                artifacts_path = self._package_artifacts(experiment_id, config.deliverables, temp_path)

                end_time = datetime.now()

                result = ExperimentResult(
                    experiment_id=experiment_id,
                    status="completed",
                    start_time=start_time,
                    end_time=end_time,
                    deliverables_status=deliverables_status,
                    artifacts_path=str(artifacts_path)
                )

                print(f"Experiment {experiment_id} completed successfully")
                return result

        except Exception as e:
            end_time = datetime.now()
            error_msg = str(e)

            result = ExperimentResult(
                experiment_id=experiment_id,
                status="failed",
                start_time=start_time,
                end_time=end_time,
                error_message=error_msg
            )

            print(f"Experiment {experiment_id} failed: {error_msg}")
            return result

    def _run_training_script(self, config: ExperimentConfig, working_dir: Path):
        """Run the training script with the provided configuration."""
        if not config.training_script:
            raise ValueError("No training script specified")

        # Prepare command arguments
        cmd = config.training_script.split()

        # Add configuration arguments
        for key, value in config.training_config.items():
            if isinstance(value, bool):
                if value:
                    cmd.append(f"--{key}")
            else:
                cmd.append(f"--{key}")
                cmd.append(str(value))

        print(f"Running command: {' '.join(cmd)}")
        print(f"Working directory: {working_dir}")

        # Run the command
        result = subprocess.run(
            cmd,
            cwd=working_dir,
            capture_output=True,
            text=True,
            check=True
        )

        if result.returncode != 0:
            raise RuntimeError(f"Training script failed: {result.stderr}")

    def _validate_deliverables(self, deliverables: List[Dict[str, Any]], working_dir: Path) -> Dict[str, Any]:
        """Validate that all expected deliverables exist."""
        status = {}

        for deliverable in deliverables:
            deliverable_type = deliverable.get('type', 'unknown')
            path = deliverable.get('path', '')
            validation = deliverable.get('validation', 'exists')

            full_path = working_dir / path

            if validation == 'exists':
                exists = full_path.exists()
                status[deliverable_type] = {
                    'status': 'delivered' if exists else 'missing',
                    'path': str(full_path),
                    'validated': exists
                }
            elif validation == 'contains_keys':
                # For JSON files, check if required keys exist
                required_keys = deliverable.get('required_keys', [])
                if full_path.exists() and full_path.suffix == '.json':
                    try:
                        with open(full_path, 'r') as f:
                            data = json.load(f)
                        has_keys = all(key in data for key in required_keys)
                        status[deliverable_type] = {
                            'status': 'delivered',
                            'path': str(full_path),
                            'validated': has_keys,
                            'missing_keys': [k for k in required_keys if k not in data] if not has_keys else []
                        }
                    except Exception as e:
                        status[deliverable_type] = {
                            'status': 'error',
                            'path': str(full_path),
                            'validated': False,
                            'error': str(e)
                        }
                else:
                    status[deliverable_type] = {
                        'status': 'missing',
                        'path': str(full_path),
                        'validated': False
                    }
            else:
                # Default to exists check
                exists = full_path.exists()
                status[deliverable_type] = {
                    'status': 'delivered' if exists else 'missing',
                    'path': str(full_path),
                    'validated': exists
                }

        return status

    def _package_artifacts(self, experiment_id: str, deliverables: List[Dict[str, Any]], working_dir: Path) -> Path:
        """Package experiment artifacts into a zip file."""
        zip_path = self.artifacts_dir / f"{experiment_id}_artifacts.zip"

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for deliverable in deliverables:
                path = deliverable.get('path', '')
                full_path = working_dir / path

                if full_path.exists():
                    if full_path.is_file():
                        zip_file.write(full_path, path)
                    elif full_path.is_dir():
                        for file_path in full_path.rglob('*'):
                            if file_path.is_file():
                                arcname = file_path.relative_to(working_dir)
                                zip_file.write(file_path, arcname)

        return zip_path

    def save_result(self, result: ExperimentResult):
        """Save experiment result to appropriate directory."""
        result_data = {
            'experiment_id': result.experiment_id,
            'status': result.status,
            'start_time': result.start_time.isoformat(),
            'end_time': result.end_time.isoformat() if result.end_time else None,
            'deliverables_status': result.deliverables_status,
            'error_message': result.error_message,
            'artifacts_path': result.artifacts_path
        }

        if result.status == 'completed':
            result_path = self.completed_dir / f"{result.experiment_id}.json"
        else:
            result_path = self.failed_dir / f"{result.experiment_id}.json"

        with open(result_path, 'w') as f:
            json.dump(result_data, f, indent=2)

        print(f"Saved result to: {result_path}")