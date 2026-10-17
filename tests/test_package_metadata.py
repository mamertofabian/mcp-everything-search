"""Behavioral tests for the published dependency contract.

The server is written against the mcp 2.x lowlevel Server API. mcp 1.x lacks
it, and an unbounded requirement let mcp 2.0 break every fresh ``uvx`` install
of the 1.x-based release, so the next major version is excluded as well.
"""

from importlib.metadata import requires

from packaging.requirements import Requirement

DISTRIBUTION = "mcp-server-everything-search"


def _requirement(name: str) -> Requirement:
    matches = [
        Requirement(r)
        for r in requires(DISTRIBUTION) or []
        if Requirement(r).name == name
    ]
    assert len(matches) == 1, f"expected one {name} requirement, got {matches}"
    return matches[0]


def test_mcp_requirement_excludes_mcp_1_and_next_major_versions():
    # Arrange
    spec = _requirement("mcp").specifier

    # Act
    allowed = [v for v in ["1.1.2", "1.30.0", "3.0.0"] if spec.contains(v)]

    # Assert
    assert allowed == []


def test_mcp_requirement_allows_mcp_2_versions():
    # Arrange
    spec = _requirement("mcp").specifier

    # Act
    allowed = [v for v in ["2.0.0", "2.3.0", "2.99.0"] if spec.contains(v)]

    # Assert
    assert allowed == ["2.0.0", "2.3.0", "2.99.0"]
