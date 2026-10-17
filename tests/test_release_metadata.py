"""Behavioral tests: every released version is documented in CHANGELOG.md."""

import re
from importlib.metadata import version
from pathlib import Path
from typing import List, Tuple

CHANGELOG = Path(__file__).resolve().parent.parent / "CHANGELOG.md"
# Exact X.Y.Z heading; pre-release suffixes like 0.3.0rc1 do not match.
HEADING = re.compile(r"^## \[?(\d+\.\d+\.\d+)\]?(?=\s|$)")
# Versions published to PyPI before this changelog existed.
PYPI_RELEASES_BEFORE_CHANGELOG = ["0.2.1", "0.1.2", "0.1.0"]


def _sections() -> List[Tuple[str, str]]:
    """(version, body) for each version heading in order, ignoring fenced code blocks."""
    sections: List[Tuple[str, str]] = []
    in_fence = False
    for line in CHANGELOG.read_text(encoding="utf-8").splitlines():
        if line.startswith("```"):
            in_fence = not in_fence
        match = None if in_fence else HEADING.match(line)
        if match:
            sections.append((match.group(1), ""))
        elif not in_fence and line.startswith("## "):
            sections.append(("", ""))  # non-version heading closes the section
        elif sections:
            v, body = sections[-1]
            sections[-1] = (v, body + line + "\n")
    return [(v, body) for v, body in sections if v]


def _versions() -> List[str]:
    return [v for v, _ in _sections()]


def _key(v: str) -> Tuple[int, ...]:
    return tuple(int(part) for part in v.split("."))


def test_installed_version_has_a_changelog_section():
    # Arrange
    installed = version("mcp-server-everything-search")

    # Act
    documented = _versions()

    # Assert
    assert installed in documented


def test_changelog_lists_newest_version_first():
    # Act
    documented = _versions()

    # Assert
    assert documented[0] == version("mcp-server-everything-search")


def test_changelog_versions_are_strictly_descending():
    # Act
    documented = _versions()

    # Assert
    assert documented == sorted(set(documented), key=_key, reverse=True)


def test_changelog_documents_every_earlier_pypi_release():
    # Act
    documented = _versions()

    # Assert
    assert [v for v in PYPI_RELEASES_BEFORE_CHANGELOG if v not in documented] == []


def test_every_changelog_section_has_content():
    # Act
    empty = [v for v, body in _sections() if not body.strip()]

    # Assert
    assert empty == []
