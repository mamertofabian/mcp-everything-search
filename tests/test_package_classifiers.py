"""Behavioral test: published Python classifiers match the supported range.

The range runs from the requires-python floor to the newest version in the CI
test matrix, so PyPI shows every version CI actually tests.
"""

from importlib.metadata import metadata
from pathlib import Path

import yaml

DISTRIBUTION = "mcp-server-everything-search"
CI = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "ci.yml"


def _minor(version: str) -> int:
    return int(version.split(".")[1])


def test_classifiers_list_every_python_version_from_floor_to_ci_maximum():
    # Arrange
    meta = metadata(DISTRIBUTION)
    floor = _minor((meta["Requires-Python"] or "").lstrip(">="))
    ci_versions = yaml.safe_load(CI.read_text(encoding="utf-8"))["jobs"]["test"][
        "strategy"
    ]["matrix"]["python-version"]
    newest = max(_minor(v) for v in ci_versions)

    # Act
    classifiers = set(meta.get_all("Classifier") or [])
    missing = [
        f"3.{m}"
        for m in range(floor, newest + 1)
        if f"Programming Language :: Python :: 3.{m}" not in classifiers
    ]

    # Assert
    assert missing == []
