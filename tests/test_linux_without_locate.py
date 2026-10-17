"""Behavioral tests: the server starts on Linux without locate/plocate.

Directories and inspectors (e.g. Glama's build checks) run the server in a
bare container and need it to start and list its tools; the missing tool is
reported when a search actually runs.
"""

import platform
import subprocess
from typing import List

import pytest
from mcp import Client
from mcp.types import TextContent

from mcp_server_everything_search import server as server_module
from mcp_server_everything_search.search_interface import LinuxSearchProvider


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _no_locate(cmd: List[str]) -> "subprocess.CompletedProcess[str]":
    return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="")


@pytest.mark.anyio
async def test_server_without_locate_lists_tools_and_reports_install_hint_on_search(
    monkeypatch,
):
    # Arrange
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    server = server_module.create_server(
        LinuxSearchProvider(run_command=_no_locate), "linux"
    )

    # Act
    async with Client(server) as client:
        tools = [t.name for t in (await client.list_tools()).tools]
        result = await client.call_tool("search", {"base": {"query": "report"}})

    # Assert
    assert tools == ["search"]
    assert result.is_error is True
    text = "\n".join(c.text for c in result.content if isinstance(c, TextContent))
    assert text.startswith("Search failed: Neither 'locate' nor 'plocate' is installed")
