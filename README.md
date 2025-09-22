# Open Research Pipeline - A concept for managing ML research experiments

A concept for an automated experiment management and analysis system for machine learning research.
This is here to inspire thought and prompt discussion, and may be expanded into a working system. Currently the code is untested and incomplete. Think of the whole repo as pseudocode.

## Overview

The Open Research Pipeline (ORP) is a standalone package that provides:

- **Experiment orchestration**: Run experiments from configuration files
- **Deliverables management**: Track and validate experiment outputs
- **Automated analysis**: AI-powered analysis of experiment results
- **Research CI/CD**: Pipeline-based experiment execution and validation

## Installation

```bash
pip install open-research-pipeline
```

Or for development:

```bash
git clone <repository-url>
cd open-research-pipeline
pip install -e ".[dev]"
```

## Quick Start

1. Create an experiment configuration:

    ```yaml
    # experiment.yaml
    experiment:
      name: "my-first-experiment"
      description: "Testing learning rate sensitivity"

    training:
      script: "python train.py"
      config:
        learning_rate: 0.001
        epochs: 10

    deliverables:
      - type: "model_checkpoint"
        path: "output/model"
        validation: "exists"
      - type: "metrics"
        path: "output/metrics.json"
        validation: "contains_keys"
        required_keys: ["accuracy", "loss"]
    ```

2. Run the experiment:

    ```bash
    orp run experiment.yaml
    ```

Notes on `training.script` and logs
-------------------------------

- `training.script` may be specified either as a string (backwards-compatible) or as a list of command arguments (recommended). Example:

```yaml
training:
  # string form (legacy)
  script: "python train.py --config=config.yaml"

  # preferred list form
  script: ["python", "train.py", "--config=config.yaml"]
```

- The runner captures the training process stdout and stderr into files named `training_stdout.txt` and `training_stderr.txt` and includes both files inside the experiment artifacts zip (`experiments/artifacts/<experiment_id>_artifacts.zip`).

- The `ExperimentResult` returned by the runner includes `artifacts_path` (path to the zip) and optional zip-qualified log paths in `training_stdout_path` and `training_stderr_path` using the format `path/to/zip::training_stdout.txt`.

## Architecture

```text
open-research-pipeline/
├── src/open_research_pipeline/
│   ├── core/           # Core experiment management
│   ├── cli/            # Command-line interface
│   ├── analysis/       # Automated analysis agents
│   └── integrations/   # External service integrations
├── tests/              # Test suite
└── docs/               # Documentation
```

## Key Features

### Experiment Management

- Configuration-driven experiment execution
- Deliverables tracking and validation
- Experiment genealogy and metadata

### Analysis Pipeline

- Automated performance analysis
- Statistical validation
- Comparative analysis across experiments

### Integrations

- Weights & Biases for metrics tracking
- Cloud storage for artifacts
- Notification systems for experiment completion

## Usage Examples

### Basic Experiment

```bash
# Run a single experiment
orp run config/experiment.yaml
```

### Batch Experiments

```bash
# Run multiple experiments in parallel
orp batch config/experiments/
```

### Queue Management

```bash
# Start queue processor
orp queue start

# Submit experiment to queue
orp queue submit config/experiment.yaml
```

### Analysis

```bash
# Analyze completed experiment
orp analyze results/experiment_001/
```

## Development

### Setup

```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/
isort src/
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License. See `LICENSE` for details.

## Contact

For questions or contributions, please open an issue on GitHub.
