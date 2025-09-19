"""Command-line interface for Open Research Pipeline."""

import click
from pathlib import Path
import os

from open_research_pipeline.core.runner import ExperimentRunner, ExperimentConfig
from open_research_pipeline.core.github_client import GitHubConfig


@click.group()
@click.version_option()
def main():
    """Open Research Pipeline - Automated experiment management system."""
    pass


@main.command()
@click.argument('config_file', type=click.Path(exists=True))
@click.option('--base-dir', default='experiments', help='Base directory for experiments')
def run(config_file, base_dir):
    """Run a single experiment from configuration file."""
    runner = ExperimentRunner(base_dir)

    try:
        # Load experiment configuration
        config = runner.load_experiment_config(config_file)

        # Run the experiment
        result = runner.run_experiment(config)

        # Save the result
        runner.save_result(result)

        if result.status == 'completed':
            click.echo(f"✅ Experiment completed successfully: {result.experiment_id}")
            click.echo(f"📦 Artifacts saved to: {result.artifacts_path}")
        else:
            click.echo(f"❌ Experiment failed: {result.experiment_id}")
            if result.error_message:
                click.echo(f"Error: {result.error_message}")
            exit(1)

    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        exit(1)


@main.command()
@click.argument('config_dir', type=click.Path(exists=True))
@click.option('--base-dir', default='experiments', help='Base directory for experiments')
@click.option('--parallel', default=1, help='Number of parallel experiments')
def batch(config_dir, base_dir, parallel):
    """Run multiple experiments from a directory of config files."""
    config_path = Path(config_dir)
    config_files = list(config_path.glob('*.yaml')) + list(config_path.glob('*.yml'))

    if not config_files:
        click.echo(f"No YAML config files found in {config_dir}")
        return

    click.echo(f"Found {len(config_files)} experiment configurations")

    runner = ExperimentRunner(base_dir)

    for config_file in config_files:
        click.echo(f"\n🔬 Running experiment: {config_file.name}")
        try:
            config = runner.load_experiment_config(str(config_file))
            result = runner.run_experiment(config)
            runner.save_result(result)

            if result.status == 'completed':
                click.echo(f"✅ Completed: {result.experiment_id}")
            else:
                click.echo(f"❌ Failed: {result.experiment_id}")

        except Exception as e:
            click.echo(f"❌ Error processing {config_file.name}: {str(e)}")


@main.command()
@click.option('--base-dir', default='experiments', help='Base directory for experiments')
def status(base_dir):
    """Show status of experiments."""
    base_path = Path(base_dir)

    completed = list((base_path / 'completed').glob('*.json'))
    failed = list((base_path / 'failed').glob('*.json'))
    queued = list((base_path / 'queue').glob('*.json'))

    click.echo("📊 Experiment Status Summary")
    click.echo(f"✅ Completed: {len(completed)}")
    click.echo(f"❌ Failed: {len(failed)}")
    click.echo(f"⏳ Queued: {len(queued)}")

    if completed:
        click.echo("\n📁 Recent Completed:")
        for result_file in sorted(completed, key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
            click.echo(f"  • {result_file.stem}")

    if failed:
        click.echo("\n❌ Recent Failed:")
        for result_file in sorted(failed, key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
            click.echo(f"  • {result_file.stem}")


@main.command()
@click.argument('experiment_id')
@click.option('--base-dir', default='experiments', help='Base directory for experiments')
def info(experiment_id, base_dir):
    """Show detailed information about a specific experiment."""
    base_path = Path(base_dir)

    # Search for the experiment in all directories
    for status_dir in ['completed', 'failed', 'queue']:
        result_file = base_path / status_dir / f"{experiment_id}.json"
        if result_file.exists():
            import json
            with open(result_file, 'r') as f:
                data = json.load(f)

            click.echo(f"🔍 Experiment: {experiment_id}")
            click.echo(f"📊 Status: {data['status']}")
            click.echo(f"🕐 Started: {data['start_time']}")

            if data.get('end_time'):
                click.echo(f"🕐 Ended: {data['end_time']}")

            if data.get('error_message'):
                click.echo(f"❌ Error: {data['error_message']}")

            if data.get('artifacts_path'):
                click.echo(f"📦 Artifacts: {data['artifacts_path']}")

            if data.get('deliverables_status'):
                click.echo("\n📋 Deliverables:")
                for deliverable_type, status in data['deliverables_status'].items():
                    icon = "✅" if status.get('validated', False) else "❌"
                    click.echo(f"  {icon} {deliverable_type}: {status.get('status', 'unknown')}")

            return

    click.echo(f"❌ Experiment {experiment_id} not found")


@main.command()
@click.option('--repo', default=None, help='GitHub repository in format owner/repo')
@click.option('--token', default=None, help='GitHub token (or set GITHUB_TOKEN env var)')
@click.option('--state', default='open', help='Issue state: open, closed, all')
@click.option('--labels', default='experiment', help='Comma-separated list of labels')
def list(repo, token, state, labels):
    """List experiments from GitHub issues."""
    try:
        # Setup GitHub config
        if not token:
            token = os.getenv('GITHUB_TOKEN')
        if not token:
            click.echo("❌ GitHub token required. Set GITHUB_TOKEN env var or use --token", err=True)
            exit(1)

        if not repo:
            repo = os.getenv('GITHUB_REPOSITORY', 'nomadicsynth/open-research-pipeline')

        github_config = GitHubConfig(
            token=token,
            repo_owner=repo.split('/')[0],
            repo_name=repo.split('/')[1]
        )

        runner = ExperimentRunner(github_config=github_config)
        experiments = runner.list_github_experiments(
            state=state,
            labels=labels.split(',') if labels else None
        )

        if not experiments:
            click.echo("No experiments found")
            return

        click.echo(f"🔬 Found {len(experiments)} experiments:")
        for exp in experiments:
            assignee = f" 👤 {exp.assignee}" if exp.assignee else ""
            click.echo(f"  #{exp.issue_number}: {exp.title}{assignee}")
            if exp.metadata.get('command'):
                click.echo(f"    Command: {exp.metadata['command']}")

    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        exit(1)


@main.command()
@click.argument('issue_number', type=int)
@click.option('--repo', default=None, help='GitHub repository in format owner/repo')
@click.option('--token', default=None, help='GitHub token (or set GITHUB_TOKEN env var)')
@click.option('--assignee', default=None, help='GitHub username to assign (defaults to token user)')
def claim(issue_number, repo, token, assignee):
    """Claim an experiment from GitHub issue."""
    try:
        # Setup GitHub config
        if not token:
            token = os.getenv('GITHUB_TOKEN')
        if not token:
            click.echo("❌ GitHub token required. Set GITHUB_TOKEN env var or use --token", err=True)
            exit(1)

        if not repo:
            repo = os.getenv('GITHUB_REPOSITORY', 'nomadicsynth/open-research-pipeline')

        github_config = GitHubConfig(
            token=token,
            repo_owner=repo.split('/')[0],
            repo_name=repo.split('/')[1]
        )

        runner = ExperimentRunner(github_config=github_config)

        # Get current user if no assignee specified
        if not assignee:
            from github import Github
            g = Github(token)
            assignee = g.get_user().login

        success = runner.claim_github_experiment(issue_number, assignee)

        if success:
            click.echo(f"✅ Successfully claimed experiment #{issue_number}")
        else:
            click.echo(f"❌ Failed to claim experiment #{issue_number} (may already be claimed)")

    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        exit(1)


@main.command()
@click.argument('issue_number', type=int)
@click.option('--repo', default=None, help='GitHub repository in format owner/repo')
@click.option('--token', default=None, help='GitHub token (or set GITHUB_TOKEN env var)')
@click.option('--base-dir', default='experiments', help='Base directory for experiments')
def run_github(issue_number, repo, token, base_dir):
    """Run an experiment from GitHub issue."""
    try:
        # Setup GitHub config
        if not token:
            token = os.getenv('GITHUB_TOKEN')
        if not token:
            click.echo("❌ GitHub token required. Set GITHUB_TOKEN env var or use --token", err=True)
            exit(1)

        if not repo:
            repo = os.getenv('GITHUB_REPOSITORY', 'nomadicsynth/open-research-pipeline')

        github_config = GitHubConfig(
            token=token,
            repo_owner=repo.split('/')[0],
            repo_name=repo.split('/')[1]
        )

        runner = ExperimentRunner(base_dir=base_dir, github_config=github_config)

        click.echo(f"🚀 Running experiment from GitHub issue #{issue_number}")
        result = runner.run_github_experiment(issue_number)

        if result.status == 'completed':
            click.echo(f"✅ Experiment completed successfully: {result.experiment_id}")
            click.echo(f"📦 Artifacts saved to: {result.artifacts_path}")
        else:
            click.echo(f"❌ Experiment failed: {result.experiment_id}")
            if result.error_message:
                click.echo(f"Error: {result.error_message}")
            exit(1)

    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        exit(1)


if __name__ == '__main__':
    main()