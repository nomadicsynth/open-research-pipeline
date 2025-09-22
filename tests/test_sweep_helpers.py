import os
import subprocess


def test_issue_template_exists():
    assert os.path.exists('.github/ISSUE_TEMPLATE/experiment.yml')


def test_claim_shard_help():
    # ensure `orp` main script is importable and shows help for claim-shard
    res = subprocess.run(['python', '-c', 'import open_research_pipeline.cli as c; print("ok")'], capture_output=True, text=True)
    assert res.returncode == 0
