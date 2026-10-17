"""Behavioral tests: server.json (MCP Registry entry) matches the published package.

The registry verifies PyPI ownership by finding `mcp-name: <server name>` in the
package README, and installs the package version named in server.json, so these
must stay in sync with pyproject on every release.
"""

import json
import re

import jsonschema
from importlib.metadata import metadata, version
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "tests" / "fixtures" / "server.schema.2025-12-11.json"
DISTRIBUTION = "mcp-server-everything-search"
NAME_PATTERN = re.compile(r"^[a-zA-Z0-9.-]+/[a-zA-Z0-9._-]+$")


def _server() -> Dict[str, Any]:
    return json.loads((ROOT / "server.json").read_text(encoding="utf-8"))


def _package() -> Dict[str, Any]:
    [package] = _server()["packages"]
    return package


def _markers(text: str, name: str) -> list:
    # Registry rule: the literal "mcp-name: <name>" followed by a boundary
    return re.findall(r"mcp-name: (" + re.escape(name) + r")(?=\s|-->|$)", text)


def test_server_name_is_declared_in_the_published_readme():
    # Arrange
    name = _server()["name"]
    published = metadata(DISTRIBUTION)["Description"] or ""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    # Act / Assert: exactly one marker, both in the source README and in the installed metadata
    assert NAME_PATTERN.match(name)
    assert _markers(readme, name) == [name]
    assert _markers(published, name) == [name]


def test_server_json_conforms_to_the_registry_schema():
    # Arrange
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    server = _server()

    # Act
    errors = [e.message for e in jsonschema.Draft7Validator(schema).iter_errors(server)]

    # Assert
    assert errors == []
    assert server["$schema"] == schema["$id"]


def test_server_json_versions_match_the_installed_package():
    installed = version(DISTRIBUTION)

    assert (_server()["version"], _package()["version"]) == (installed, installed)


def test_server_json_points_at_the_pypi_stdio_package():
    package = _package()

    assert (package["registryType"], package["identifier"]) == ("pypi", DISTRIBUTION)
    assert package["transport"] == {"type": "stdio"}


def test_server_json_declares_every_environment_variable_the_server_reads():
    # Arrange
    variables = {v["name"]: v for v in _package()["environmentVariables"]}

    # Assert: both are optional for the registry (SDK path is Windows-only)
    assert set(variables) == {"EVERYTHING_SDK_PATH", "EVERYTHING_SEARCH_TOOL_NAME"}
    assert not any(v.get("isRequired") for v in variables.values())
    assert "Windows" in variables["EVERYTHING_SDK_PATH"]["description"]
    assert not any(v.get("isSecret") for v in variables.values())
    assert variables["EVERYTHING_SEARCH_TOOL_NAME"].get("default") == "search"


def test_server_json_description_fits_the_registry_limit():
    description = _server()["description"]

    assert 1 <= len(description) <= 100
