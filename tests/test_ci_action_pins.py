"""Behavioral tests: CI actions are pinned to exact release tags.

astral-sh/setup-uv publishes only exact tags (no moving v10 major tag), so
`@v10` failed to resolve on GitHub and every CI job failed at setup. Exact
vX.Y.Z tags always resolve and make upgrades explicit.
"""

import re
from pathlib import Path
from typing import List

import yaml

WORKFLOW = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "ci.yml"
EXACT_TAG = re.compile(r"^[\w.-]+/[\w.-]+@v\d+\.\d+\.\d+$")


def _action_refs() -> List[str]:
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    return [
        step["uses"]
        for job in workflow["jobs"].values()
        for step in job["steps"]
        if "uses" in step
    ]


def test_every_ci_action_is_pinned_to_an_exact_release_tag():
    # Arrange
    refs = _action_refs()

    # Act
    loose = [ref for ref in refs if not EXACT_TAG.match(ref)]

    # Assert
    assert refs != []
    assert loose == []
