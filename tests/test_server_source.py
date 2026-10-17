"""Behavioral tests for server.py source hygiene (PR #11).

The platform syntax guides contain literal backslashes (``\\.``, ``C:\\Projects``).
In non-raw strings these are invalid escape sequences, which emit
SyntaxWarning on Python 3.12+ every time the module is compiled.
"""

import hashlib
import importlib.util
import platform
import warnings
from pathlib import Path

import pytest

from mcp_server_everything_search import server as server_module


def test_server_source_compiles_without_invalid_escape_warnings():
    # Arrange
    spec = importlib.util.find_spec("mcp_server_everything_search.server")
    assert spec is not None and spec.origin is not None
    source = Path(spec.origin).read_text(encoding="utf-8")

    # Act / Assert: invalid escapes raise instead of warning
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        code = compile(source, spec.origin, "exec")

    assert code is not None


@pytest.mark.parametrize(
    ("platform_name", "system", "literal"),
    [
        ("Windows", "windows", "path:C:\\Projects *.js"),
        ("Linux", "linux", 'locate -r "/home/.*\\.txt$"'),
    ],
)
def test_syntax_guides_keep_literal_backslashes(
    monkeypatch, platform_name, system, literal
):
    # Arrange
    monkeypatch.setattr(platform, "system", lambda: platform_name)

    # Act
    description = server_module.build_search_tool(system).description or ""

    # Assert
    assert literal in description


@pytest.mark.parametrize(
    ("platform_name", "system", "sha256"),
    [
        (
            "Windows",
            "windows",
            "bb88177f91681fe7d7ebebda238feb0ff75587cbc393747efc75087448568974",
        ),
        (
            "Darwin",
            "darwin",
            "8484addd2aa6a152e7ff92ae3ea7f1d51f051e3846cb6d56ed5275c6b2f8edaa",
        ),
        (
            "Linux",
            "linux",
            "3a737f36d2b68b3e94610f85606898a1228ee30347e1fc5da49fe1b9dc586e6e",
        ),
    ],
)
def test_tool_description_text_is_unchanged(monkeypatch, platform_name, system, sha256):
    # Characterization: full description text as of 2558ab2, so raw-string edits cannot alter it.
    monkeypatch.setattr(platform, "system", lambda: platform_name)

    description = server_module.build_search_tool(system).description or ""

    assert hashlib.sha256(description.encode("utf-8")).hexdigest() == sha256
