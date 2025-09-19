"""GitHub integration for experiment management."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from github import Github
from github.Issue import Issue
from github.Repository import Repository


@dataclass
class GitHubConfig:
    """Configuration for GitHub integration."""

    token: str
    repo_owner: str
    repo_name: str
    base_url: Optional[str] = None

    @classmethod
    def from_env(cls) -> GitHubConfig:
        """Create config from environment variables."""
        token = os.getenv('GITHUB_TOKEN')
        if not token:
            raise ValueError("GITHUB_TOKEN environment variable is required")

        repo = os.getenv('GITHUB_REPOSITORY', 'nomadicsynth/open-research-pipeline')
        if '/' not in repo:
            raise ValueError("GITHUB_REPOSITORY must be in format 'owner/repo'")

        owner, name = repo.split('/', 1)

        return cls(
            token=token,
            repo_owner=owner,
            repo_name=name,
            base_url=os.getenv('GITHUB_API_URL')
        )


@dataclass
class ExperimentIssue:
    """Represents an experiment from a GitHub issue."""

    issue_number: int
    title: str
    body: str
    labels: List[str]
    assignee: Optional[str]
    state: str
    metadata: Dict[str, Any]

    @classmethod
    def from_issue(cls, issue: Issue) -> ExperimentIssue:
        """Create ExperimentIssue from GitHub Issue object."""
        # Parse metadata from issue body
        metadata = cls._parse_metadata(issue.body or "")

        return cls(
            issue_number=issue.number,
            title=issue.title,
            body=issue.body or "",
            labels=[label.name for label in issue.labels],
            assignee=issue.assignee.login if issue.assignee else None,
            state=issue.state,
            metadata=metadata
        )

    @staticmethod
    def _parse_metadata(body: str) -> Dict[str, Any]:
        """Parse YAML metadata block from issue body."""
        import yaml

        # Look for YAML block between --- markers
        pattern = r'---\s*\n(.*?)\n---'
        match = re.search(pattern, body, re.DOTALL)

        if match:
            try:
                return yaml.safe_load(match.group(1))
            except yaml.YAMLError:
                pass

        return {}


class GitHubClient:
    """Client for GitHub operations related to experiments."""

    def __init__(self, config: GitHubConfig):
        self.config = config
        self.github = Github(
            login_or_token=config.token,
            base_url=config.base_url
        )
        self.repo: Repository = self.github.get_repo(f"{config.repo_owner}/{config.repo_name}")

    def list_experiments(self, state: str = "open", labels: Optional[List[str]] = None) -> List[ExperimentIssue]:
        """List experiment issues from the repository."""
        if labels is None:
            labels = ["experiment"]

        issues = self.repo.get_issues(state=state, labels=labels)
        return [ExperimentIssue.from_issue(issue) for issue in issues]

    def get_experiment(self, issue_number: int) -> ExperimentIssue:
        """Get a specific experiment issue."""
        issue = self.repo.get_issue(issue_number)
        return ExperimentIssue.from_issue(issue)

    def claim_experiment(self, issue_number: int, assignee: str) -> bool:
        """Claim an experiment by assigning it and adding claimed label."""
        try:
            issue = self.repo.get_issue(issue_number)

            # Check if already claimed
            if issue.assignee:
                return False

            # Assign the user
            user = self.github.get_user(assignee)
            issue.edit(assignee=user)

            # Add claimed label if it exists
            try:
                claimed_label = self.repo.get_label("claimed")
                issue.add_to_labels(claimed_label)
            except:
                # Label doesn't exist, create it
                self.repo.create_label("claimed", "FFA500")
                claimed_label = self.repo.get_label("claimed")
                issue.add_to_labels(claimed_label)

            # Add comment
            issue.create_comment(f"Experiment claimed by @{assignee}")

            return True

        except Exception as e:
            print(f"Failed to claim experiment: {e}")
            return False

    def update_experiment_status(self, issue_number: int, status: str, comment: Optional[str] = None):
        """Update experiment status with label and optional comment."""
        try:
            issue = self.repo.get_issue(issue_number)

            # Remove existing status labels
            status_labels = ["claimed", "in-progress", "completed", "failed"]
            for label in issue.labels:
                if label.name in status_labels:
                    issue.remove_from_labels(label)

            # Add new status label
            try:
                status_label = self.repo.get_label(status)
            except:
                # Create label if it doesn't exist
                color_map = {
                    "claimed": "FFA500",
                    "in-progress": "FFFF00",
                    "completed": "00FF00",
                    "failed": "FF0000"
                }
                self.repo.create_label(status, color_map.get(status, "000000"))
                status_label = self.repo.get_label(status)

            issue.add_to_labels(status_label)

            # Add comment if provided
            if comment:
                issue.create_comment(comment)

        except Exception as e:
            print(f"Failed to update experiment status: {e}")

    def add_experiment_comment(self, issue_number: int, comment: str):
        """Add a comment to an experiment issue."""
        try:
            issue = self.repo.get_issue(issue_number)
            issue.create_comment(comment)
        except Exception as e:
            print(f"Failed to add comment: {e}")

    def upload_artifact_to_issue(self, issue_number: int, file_path: str, artifact_name: str):
        """Upload an artifact file to an issue as a comment with link."""
        try:
            # For now, just add a comment with the file path
            # In a real implementation, you might upload to GitHub Releases or external storage
            issue = self.repo.get_issue(issue_number)
            comment = f"Artifact uploaded: {artifact_name}\n\nFile: {file_path}"
            issue.create_comment(comment)
        except Exception as e:
            print(f"Failed to upload artifact: {e}")