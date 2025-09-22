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
from typing import Any, Dict, List, Optional, Tuple, Union

import yaml

from .github_client import GitHubClient, GitHubConfig, ExperimentIssue


@dataclass
class ExperimentConfig:
    """Configuration for a single experiment."""

    name: str
    description: str = ""
    # Accept either a shell string or a list of command arguments (preferred)
    training_script: Union[str, List[str]] = ""
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
    training_stdout_path: Optional[str] = None
    training_stderr_path: Optional[str] = None

    def __post_init__(self):
        if self.deliverables_status is None:
            self.deliverables_status = {}


class ExperimentRunner:
    """Core experiment runner that orchestrates training and validation."""

    def __init__(self, base_dir: str = "experiments", github_config: Optional[GitHubConfig] = None):
        self.base_dir = Path(base_dir)
        self.queue_dir = self.base_dir / "queue"
        self.completed_dir = self.base_dir / "completed"
        self.failed_dir = self.base_dir / "failed"
        self.artifacts_dir = self.base_dir / "artifacts"

        # GitHub integration
        self.github_client: Optional[GitHubClient] = None
        if github_config:
            self.github_client = GitHubClient(github_config)

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

        # We'll create a temporary directory manually (mkdtemp) so we can copy logs on failure
        temp_dir = tempfile.mkdtemp()
        temp_path = Path(temp_dir)

        try:
            # Run the training script
            self._run_training_script(config, temp_path)

            # Validate deliverables
            deliverables_status = self._validate_deliverables(config.deliverables, temp_path)

            # Package artifacts (zip path)
            zip_path = self._package_artifacts(experiment_id, config.deliverables, temp_path)

            end_time = datetime.now()

            result = ExperimentResult(
                experiment_id=experiment_id,
                status="completed",
                start_time=start_time,
                end_time=end_time,
                deliverables_status=deliverables_status,
                artifacts_path=str(zip_path) if zip_path else None,
                training_stdout_path=(f"{zip_path}::training_stdout.txt") if (temp_path / "training_stdout.txt").exists() else None,
                training_stderr_path=(f"{zip_path}::training_stderr.txt") if (temp_path / "training_stderr.txt").exists() else None,
            )

            print(f"Experiment {experiment_id} completed successfully")
            return result

        except Exception as e:
            # Create artifacts zip (include any logs present) so logs end up in the experiment zip
            try:
                zip_path = self._package_artifacts(experiment_id, config.deliverables, temp_path)
            except Exception:
                zip_path = None

            # Attempt to record zip-qualified paths for logs
            end_time = datetime.now()
            error_msg = str(e)

            # If logs exist in the working dir, record their paths inside the zip using a 'zip-qualified' string
            stdout_zip_path = None
            stderr_zip_path = None
            try:
                if zip_path and (temp_path / "training_stdout.txt").exists():
                    stdout_zip_path = f"{zip_path}::training_stdout.txt"
                if zip_path and (temp_path / "training_stderr.txt").exists():
                    stderr_zip_path = f"{zip_path}::training_stderr.txt"
            except Exception:
                pass

            # Clean up the temporary directory
            try:
                shutil.rmtree(temp_path)
            except Exception:
                pass

            result = ExperimentResult(
                experiment_id=experiment_id,
                status="failed",
                start_time=start_time,
                end_time=end_time,
                error_message=error_msg,
                artifacts_path=str(zip_path) if zip_path else None,
                training_stdout_path=stdout_zip_path,
                training_stderr_path=stderr_zip_path,
            )

            print(f"Experiment {experiment_id} failed: {error_msg}")
            return result
        finally:
            # If the directory still exists (e.g., success path didn't remove it), remove it
            try:
                if temp_path.exists():
                    shutil.rmtree(temp_path)
            except Exception:
                pass

    def _run_training_script(self, config: ExperimentConfig, working_dir: Path):
        """Run the training script with the provided configuration."""
        if not config.training_script:
            raise ValueError("No training script specified")

        # Prepare command arguments. Support list (preferred) or string for backward compatibility.
        if isinstance(config.training_script, list):
            cmd = config.training_script
        else:
            cmd = str(config.training_script).split()

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

        # Files to capture stdout/stderr
        stdout_path = working_dir / "training_stdout.txt"
        stderr_path = working_dir / "training_stderr.txt"

        # Run the command and stream stdout/stderr directly to files to avoid large memory use
        with open(stdout_path, 'w', encoding='utf-8') as f_out, open(stderr_path, 'w', encoding='utf-8') as f_err:
            proc = subprocess.run(
                cmd,
                cwd=working_dir,
                stdout=f_out,
                stderr=f_err,
                text=True
            )

        if proc.returncode != 0:
            # Provide a brief message; full logs are available in the files
            raise RuntimeError(f"Training script failed (exit {proc.returncode}). See training_stderr.txt for details.")

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
        """Package experiment artifacts into a zip file.

        Returns the path to the artifacts zip. The zip will include any deliverables that exist
        in the working directory and the training log files `training_stdout.txt` and
        `training_stderr.txt` when present.
        """
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

            # Also include training stdout/stderr if present in working dir
            stdout_path = working_dir / "training_stdout.txt"
            stderr_path = working_dir / "training_stderr.txt"

            if stdout_path.exists():
                zip_file.write(stdout_path, "training_stdout.txt")
            if stderr_path.exists():
                zip_file.write(stderr_path, "training_stderr.txt")

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
            'artifacts_path': result.artifacts_path,
            'training_stdout_path': result.training_stdout_path,
            'training_stderr_path': result.training_stderr_path
        }

        if result.status == 'completed':
            result_path = self.completed_dir / f"{result.experiment_id}.json"
        else:
            result_path = self.failed_dir / f"{result.experiment_id}.json"

        with open(result_path, 'w') as f:
            json.dump(result_data, f, indent=2)

        print(f"Saved result to: {result_path}")

    # GitHub integration methods
    def list_github_experiments(self, state: str = "open", labels: Optional[List[str]] = None) -> List[ExperimentIssue]:
        """List experiments from GitHub issues."""
        if not self.github_client:
            raise ValueError("GitHub client not configured")
        return self.github_client.list_experiments(state=state, labels=labels)

    def get_github_experiment(self, issue_number: int) -> ExperimentIssue:
        """Get experiment details from GitHub issue."""
        if not self.github_client:
            raise ValueError("GitHub client not configured")
        return self.github_client.get_experiment(issue_number)

    def claim_github_experiment(self, issue_number: int, assignee: str) -> bool:
        """Claim an experiment on GitHub."""
        if not self.github_client:
            raise ValueError("GitHub client not configured")
        return self.github_client.claim_experiment(issue_number, assignee)

    def run_github_experiment(self, issue_number: int) -> ExperimentResult:
        """Run an experiment from GitHub issue."""
        if not self.github_client:
            raise ValueError("GitHub client not configured")

        # Get experiment from GitHub
        experiment_issue = self.get_github_experiment(issue_number)

        # Parse config from metadata
        config = self._config_from_github_issue(experiment_issue)

        # Update status to in-progress
        self.github_client.update_experiment_status(
            issue_number,
            "in-progress",
            "Starting experiment execution..."
        )

        try:
            # Run the experiment
            result = self.run_experiment(config)

            # Update status based on result
            if result.status == "completed":
                self.github_client.update_experiment_status(
                    issue_number,
                    "completed",
                    f"Experiment completed successfully. Artifacts: {result.artifacts_path}"
                )
            else:
                self.github_client.update_experiment_status(
                    issue_number,
                    "failed",
                    f"Experiment failed: {result.error_message}"
                )

            return result

        except Exception as e:
            # Update status on failure
            self.github_client.update_experiment_status(
                issue_number,
                "failed",
                f"Experiment execution failed: {str(e)}"
            )
            raise

    def _config_from_github_issue(self, issue: ExperimentIssue) -> ExperimentConfig:
        """Create ExperimentConfig from GitHub issue metadata."""
        metadata = issue.metadata

        return ExperimentConfig(
            name=metadata.get('title', issue.title),
            description=issue.body,
            training_script=metadata.get('command', ''),
            training_config={},  # Could parse additional config from metadata
            deliverables=[],     # Could define deliverables in metadata
            metadata=metadata
        )