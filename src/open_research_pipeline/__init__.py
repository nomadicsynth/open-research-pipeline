"""Open Research Pipeline - Automated experiment management system."""

__version__ = "0.1.0"

from .core.runner import ExperimentRunner, ExperimentConfig, ExperimentResult

__all__ = [
    "ExperimentRunner",
    "ExperimentConfig",
    "ExperimentResult",
]