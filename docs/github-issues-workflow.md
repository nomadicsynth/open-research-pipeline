# GitHub Issues-Based Research Workflow

## Overview

This document outlines a workflow for managing research projects using GitHub repositories where experiments are tracked as issues. This approach enables open, collaborative research where anyone can contribute to experiments, propose new ones, and track progress through GitHub's issue system.

## Core Concept

- **One Research Project = One GitHub Repo**: Each research project has its own repository
- **Experiments as Issues**: Individual experiments are represented as GitHub issues tagged with configurable labels
- **Open Collaboration**: Anyone can propose, claim, and contribute to experiments
- **Pipeline Integration**: The research pipeline interacts with GitHub issues to discover, run, and report on experiments

## Interaction Patterns

### For Contributors

- **Discovery**: Browse issues labeled as `experiment` across configured repositories
- **Claiming**: Assign yourself to an experiment issue and add `claimed` label
- **Execution**: Run experiments locally or via the pipeline
- **Contribution**: Submit results, code changes, or follow-up experiments via PRs

### For Maintainers

- **Triage**: Review new experiment proposals and apply appropriate labels
- **Oversight**: Monitor progress, assign reviewers, and manage resources
- **Governance**: Set policies for claiming, running, and archiving experiments

### Via Pipeline CLI

- `orp list` - List available experiments from GitHub issues
- `orp claim <issue>` - Claim an experiment
- `orp run <issue>` - Execute an experiment
- `orp upload-results <issue> <path>` - Attach artifacts to an issue

## Issue Lifecycle and Workflow

### 1. Propose an Experiment

- Create a new issue using the `Experiment` template
- Include structured metadata in the issue body
- Add relevant labels: `experiment`, domain tags, difficulty level

### 2. Triage and Review

- Maintainers review the proposal
- Add labels like `good-first-experiment`, `needs-data`, `blocked`
- Set priority and assign to milestones if accepted

### 3. Claim the Experiment

- Contributor assigns themselves and adds `claimed` label
- Pipeline or bot can enforce single-claimer rules

### 4. Prepare and Execute

- Fork or branch if code changes needed
- Run experiment locally or trigger pipeline execution
- Record provenance: commit SHA, environment, datasets, seeds

### 5. Publish Results

- Attach artifacts (small files in repo, large files externally)
- Post summary comment with metrics and links
- Create PR if code changes are required

### 6. Review and Archive

- Reviewers validate results
- Add `completed` or `failed` labels
- Archive successful experiments with `reproducible` tag

## Labels Taxonomy

### Status Labels

- `experiment` - Primary label for all experiment issues
- `proposal` - New experiment proposal under review
- `claimed` - Experiment is being worked on
- `in-progress` - Experiment execution in progress
- `completed` - Experiment successfully completed
- `failed` - Experiment execution failed
- `archived` - Experiment archived (successful or abandoned)

### Help and Onboarding

- `good-first-experiment` - Suitable for new contributors
- `help-wanted` - Needs additional contributors
- `needs-review` - Results ready for review

### Requirements

- `needs-data` - Requires dataset preparation
- `large-dataset` - Involves large datasets
- `requires-gpu` - Needs GPU resources

### Meta Tags

- `reproducible` - Results are reproducible
- `non-reproducible` - Results not reproducible
- `benchmark` - Benchmarking experiment
- `ablation` - Ablation study

## Issue Metadata Schema

Each experiment issue should include a structured metadata block at the top:

```yaml
---
title: Short experiment title
owner: GitHub handle or none
tags: [experiment, domain, type]
priority: low|medium|high
status: open|claimed|in-progress|completed|failed
# Command: either a shell string (legacy) or a list of arguments (preferred).
# When using a list, write the command as YAML sequence, for example:
# command: ["python", "train.py", "--config=config.yaml"]
# The runner captures training logs (stdout/stderr) and includes them inside the
# artifacts zip created for the experiment (e.g. experiments/artifacts/exp_..._artifacts.zip)
command: docker run ... OR python train.py --config=config.yaml
env: container-image: "ghcr.io/org/image:tag"
dataset: name + version + url
seed: 42
expected-runtime: "2h"
artifact-location: "experiments/artifacts/#{issue}" or external URL
notes: Brief description and reproducibility assumptions
---
```

## Pipeline Integration

### Discovery

- Use GitHub API to search for issues with `label:experiment`
- Support configurable repository lists or organization-wide scanning
- Index issues for CLI/UI access

### Claiming and Permissions

- CLI command to claim issues via GitHub API
- Check assignments and labels to prevent concurrent claims
- Add claim comments with runner information

### Execution

- Two approaches:
  1. **Runner-external**: Pipeline pulls repo, reads metadata, runs locally/remotely
  2. **GitHub Actions**: Dispatch workflows for execution on GitHub runners

### Reporting

- Post status updates as comments or label changes
- Upload artifacts to issues or external storage
- Include checksums and DOIs for long-term archiving

### Automation

- Auto-triage bot for label application
- Repro-run bot for periodic validation
- CI checks on experiment-related changes

## Multi-Repo Considerations

### One Repo Per Project

- **Pros**: Local context, easier code-experiment linkage, simpler permissions
- **Cons**: Experiments scattered across repos

### Central Experiments Repo

- **Pros**: Centralized discovery and management
- **Cons**: Potential bottleneck, governance challenges

### Recommended Approach

- Pipeline remains repo-agnostic
- Configurable repo/org lists for scanning
- Treat each experiment issue as a first-class entity

## Provenance and Reproducibility

### Required Metadata

- **Code**: Commit SHA, branch, diff summary
- **Environment**: Container image or dependency specs
- **Command**: Exact execution command and config
- **Data**: Dataset name, version, URL, checksums
- **Randomness**: Seeds, random state, concurrency settings

### Artifact Storage

- **Small artifacts** (<100MB): Store in repo under `experiments/artifacts/<issue>/`
- **Large artifacts**: External storage (S3, Zenodo) with links
- **Long-term**: Archive to Zenodo for DOI assignment

### Reproducibility Checks

- Periodic re-runs of `reproducible` experiments
- Metric drift detection within tolerance
- Statistical reporting for non-deterministic results

## Governance and Contributor Experience

### Documentation

- `CONTRIBUTING.md`: Workflow explanation, label definitions, policies
- `EXPERIMENT_TEMPLATE.md`: Issue template with metadata schema
- Resource limits and quota policies

### Onboarding

- `good-first-experiment` label for newcomers
- Clear documentation and examples
- Short feedback loops

### Resource Management

- Label experiments requiring special resources (`requires-gpu`)
- Timeout and quota enforcement
- Fair allocation policies

## Edge Cases and Mitigations

### Concurrent Claims

- Atomic checks of assignment and `claimed` label
- Optimistic locking or claim tokens

### Large/Private Datasets

- Require dataset links and checksums
- Support smoke runs with synthetic data subsets

### Stale Experiments

- Automation to ping assignees after inactivity
- Auto-archive after grace period

### Flaky Results

- Multiple replicate runs
- Statistical analysis and reporting
- `non-reproducible` labeling

### Repo Changes

- Store permanent links (repo + commit SHA)
- Backup metadata to central index

## Implementation Roadmap

### Phase 1: Core Infrastructure

- Create `Experiment` issue template
- Define and document label taxonomy
- Implement basic discovery and claiming CLI commands

### Phase 2: Execution Integration

- Add GitHub Actions for experiment runs
- Implement artifact upload and result reporting
- Add provenance capture

### Phase 3: Automation and Scaling

- Auto-triage and repro-run bots
- Multi-repo support and aggregation
- Advanced filtering and search

### Phase 4: Ecosystem Growth

- Community guidelines and best practices
- Integration with research tools (Jupyter, DVC)
- Metrics and analytics dashboard

## CLI Usage Examples

```bash
# List available experiments
orp list --repo nomadicsynth/open-research-pipeline

# Claim an experiment
orp claim 123

# Run an experiment
orp run 123

# Upload results
orp upload-results 123 ./results/
```

## GitHub Actions Integration

Example workflow for experiment execution:

```yaml
name: Run Experiment
on:
  workflow_dispatch:
    inputs:
      issue_number:
        required: true
      config:
        required: true

jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run experiment
        run: python run_experiment.py --issue ${{ github.event.inputs.issue_number }}
      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          path: results/
```

This workflow enables remote execution of experiments with proper artifact management and can be triggered by the pipeline or manually.

## Setup and Installation

### Prerequisites

- Python 3.8+
- GitHub account with repository access
- GitHub Personal Access Token with `repo` and `issues` permissions

### Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/nomadicsynth/open-research-pipeline.git
    cd open-research-pipeline
    ```

2. Install dependencies:

    ```bash
    pip install -e .
    ```

3. Set up GitHub authentication:

    ```bash
    export GITHUB_TOKEN=your_personal_access_token
    export GITHUB_REPOSITORY=your-org/your-repo
    ```

### Environment Variables

- `GITHUB_TOKEN`: Your GitHub Personal Access Token
- `GITHUB_REPOSITORY`: Repository in format `owner/repo` (defaults to `nomadicsynth/open-research-pipeline`)

## CLI Usage Examples

### Basic Commands

```bash
# List all open experiments
orp list

# List experiments from specific repo
orp list --repo myorg/research-repo

# List experiments with specific labels
orp list --labels experiment,nlp

# Claim an experiment
orp claim 123

# Claim for specific user
orp claim 123 --assignee otheruser

# Run experiment from GitHub issue
orp run-github 123

# Run with custom base directory
orp run-github 123 --base-dir ./my-experiments
```

### Integration with Existing Commands

```bash
# Run local experiment (existing functionality)
orp run config.yaml

# Run batch experiments (existing functionality)
orp batch ./configs/

# Check experiment status (existing functionality)
orp status

# Get experiment details (existing functionality)
orp info exp_20231201_120000
```

## Sweep: claim-and-run

To run a parameter sweep with community volunteers with minimal owner setup, use the "claim-by-comment" pattern:

- Create an experiment issue using the `Experiment` template and include a `sweep` metadata block (see the template for an example).
- Volunteers claim a shard by posting a comment like `claim shard 17` on the issue, or by using the `orp claim-shard` helper (included in `orp` CLI) which posts a standardized claim comment and token.
- Volunteers run the experiment locally (or via their own runners), upload artifacts to agreed storage (S3/GCS/Zenodo), and post a result comment including the claim token and artifact URL.

Owner responsibilities (minimal):

- Add the issue using the template (one-time).
- Optionally provide a small public sample dataset for volunteers to do smoke runs.
- Optionally run the aggregation Action (one-click) to collect artifact links and summarize results.

Volunteer steps (copy-paste):

```bash
# Authenticate with gh (GitHub CLI) or set GITHUB_TOKEN
gh auth login

# Claim a shard (issue 123, shard 17 out of 200)
orp claim-shard 123 17 --total 200

# Run locally (example)
export SHARD=17/200
orp run --shard "$SHARD"

# Upload artifacts and post result
aws s3 cp results/shard-17.zip s3://my-bucket/experiments/123/shard-17.zip
gh issue comment 123 --body "Completed shard 17/200 (token <token>): s3://my-bucket/experiments/123/shard-17.zip\nmetrics: accuracy=0.82"
```

This pattern requires no infra maintained by the repo owner. Occasional duplicate claims are possible; volunteers should check existing comments before running. See the docs section on provenance for recommended metadata to include in claim and result comments.

### Note: specifying the repository for GitHub commands

Commands in the `orp` CLI that interact with GitHub require an explicit repository target. You must either pass `--repo owner/repo` to the command or set the `GITHUB_REPOSITORY` environment variable in your shell. This avoids accidental operations on the wrong repository.

Examples:

```bash
# supply repo explicitly
orp list --repo myorg/myrepo --token "$GITHUB_TOKEN"

# or export once in your shell
export GITHUB_REPOSITORY="myorg/myrepo"
orp claim-shard 123 17 --total 200
```

Minimal token scopes for volunteers

- For public repositories: `public_repo` (or use `gh auth login` which scopes appropriately).
- For private repositories: `repo` scope is required for posting comments and editing labels.

If neither `--repo` nor `GITHUB_REPOSITORY` is provided, `orp` will print an error and exit.

## GitHub Actions Integration

Create `.github/workflows/run-experiment.yml`:

```yaml
name: Run Experiment
on:
  workflow_dispatch:
    inputs:
      issue_number:
        description: 'Experiment issue number'
        required: true
        type: number

jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: pip install -e .

      - name: Run experiment
        run: orp run-github ${{ github.event.inputs.issue_number }}
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GITHUB_REPOSITORY: ${{ github.repository }}
```

## Repository Setup

### Issue Templates

Create `.github/ISSUE_TEMPLATE/experiment.yml`:

```yaml
name: Experiment Proposal
description: Propose a new research experiment
title: "[EXPERIMENT] "
labels: ["experiment", "proposal"]
body:
  - type: textarea
    id: description
    attributes:
      label: Experiment Description
      description: Detailed description of the experiment
    validations:
      required: true

  - type: textarea
    id: metadata
    attributes:
      label: Experiment Metadata
      description: YAML metadata block for the experiment
      value: |
        ---
        title: Experiment title
        owner: your-github-username
        tags: [experiment, domain]
        priority: low|medium|high
        status: open
        command: python train.py --config=config.yaml
        env: container-image: "ghcr.io/org/image:tag"
        dataset: name + version + url
        seed: 42
        expected-runtime: "2h"
        artifact-location: "experiments/artifacts/#{issue}"
        notes: reproducibility assumptions
        ---
    validations:
      required: true
```

### Labels Setup

Create the following labels in your repository:

- `experiment` (primary label)
- `proposal`, `claimed`, `in-progress`, `completed`, `failed`, `archived`
- `good-first-experiment`, `help-wanted`, `needs-review`
- `needs-data`, `large-dataset`, `requires-gpu`
- `reproducible`, `non-reproducible`, `benchmark`, `ablation`

## Advanced Usage

### Custom Experiment Runners

Extend the `ExperimentRunner` class for custom execution logic:

```python
from open_research_pipeline.core.runner import ExperimentRunner

class CustomRunner(ExperimentRunner):
    def _run_training_script(self, config, working_dir):
        # Custom execution logic
        pass
```

### Multi-Repository Support

The pipeline supports multiple repositories:

```bash
# List experiments across repos (requires custom implementation)
orp list --repos repo1,repo2,repo3
```

### Automation Scripts

Create scripts for automated experiment management:

```python
#!/usr/bin/env python3
from open_research_pipeline.core.github_client import GitHubClient, GitHubConfig

# Auto-assign stale experiments
def auto_assign_stale_experiments():
    config = GitHubConfig.from_env()
    client = GitHubClient(config)

    experiments = client.list_experiments(labels=["experiment", "claimed"])
    # Implementation for checking staleness and reassigning
```

This setup provides a complete workflow for managing research experiments through GitHub issues, enabling collaborative, reproducible, and automated research execution.
