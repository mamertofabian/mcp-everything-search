"""Behavioral tests for the MCP server on the mcp 2.x lowlevel API.

Handlers are exercised through a real in-memory MCP client session with a fake
search provider; platform.system() is stubbed so every platform runs anywhere.
"""

import json
import platform
import subprocess
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

import anyio
import pytest
from mcp import Client, ClientSession, MCPError
from mcp.shared.memory import create_client_server_memory_streams
from pydantic import ValidationError

from mcp_server_everything_search import server as server_module
from mcp_server_everything_search.platform_search import UnifiedSearchQuery
from mcp_server_everything_search.search_interface import (
    MacSearchProvider,
    SearchProvider,
    SearchResult,
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def _no_ambient_tool_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EVERYTHING_SEARCH_TOOL_NAME", raising=False)


@pytest.fixture
def on_platform(monkeypatch: pytest.MonkeyPatch):
    def _set(name: str) -> None:
        monkeypatch.setattr(platform, "system", lambda: name)

    return _set


class FakeSearchProvider(SearchProvider):
    """In-memory provider that records each search and returns canned results."""

    def __init__(
        self,
        results: Optional[List[SearchResult]] = None,
        error: Optional[Exception] = None,
    ):
        self.results = results or []
        self.error = error
        self.calls: List[Dict[str, Any]] = []

    def search_files(
        self,
        query: str,
        max_results: int = 100,
        match_path: bool = False,
        match_case: bool = False,
        match_whole_word: bool = False,
        match_regex: bool = False,
        sort_by: Optional[int] = None,
        **kwargs: Any,
    ) -> List[SearchResult]:
        # Record Windows options only when the Windows path supplied them (it always sets sort_by).
        if (
            sort_by is not None
            or match_path
            or match_case
            or match_whole_word
            or match_regex
        ):
            kwargs.update(
                match_path=match_path,
                match_case=match_case,
                match_whole_word=match_whole_word,
                match_regex=match_regex,
                sort_by=sort_by,
            )
        self.calls.append({"query": query, "max_results": max_results, **kwargs})
        if self.error:
            raise self.error
        return self.results

    def count_files(
        self,
        query: str,
        ignore_case: bool = True,
        regex_search: bool = False,
        existing_files: bool = True,
    ) -> int:
        self.calls.append(
            {
                "count": query,
                "ignore_case": ignore_case,
                "regex_search": regex_search,
                "existing_files": existing_files,
            }
        )
        return 70


REPORT = SearchResult(
    path=r"C:\docs\report.pdf",
    filename="report.pdf",
    extension="pdf",
    size=1234567,
    created=datetime(2026, 1, 2, 3, 4, 5),
    modified=datetime(2026, 2, 3, 4, 5, 6),
    accessed=None,
)

REPORT_TEXT = (
    "Path: C:\\docs\\report.pdf\n"
    "Filename: report.pdf (pdf)\n"
    "Size: 1,234,567 bytes\n"
    "Created: 2026-01-02 03:04:05\n"
    "Modified: 2026-02-03 04:05:06\n"
    "Accessed: N/A\n"
)


def _text(result: Any) -> str:
    return "\n".join(c.text for c in result.content)


# --- build_search_tool ---


def test_build_search_tool_windows_uses_platform_schema_and_everything_docs(
    on_platform,
):
    # Arrange
    on_platform("Windows")

    # Act
    tool = server_module.build_search_tool("windows")

    # Assert
    description = tool.description or ""
    assert tool.name == "search"
    assert tool.input_schema == UnifiedSearchQuery.get_schema_for_platform()
    assert description.splitlines()[0] == "Universal file search tool for Windows"
    assert "Using Everything SDK with full search capabilities" in description
    assert "datemodified:<date>, dm:<date>: Modified date" in description
    assert "ext:py datemodified:today" in description


def test_build_search_tool_linux_describes_locate(on_platform):
    on_platform("Linux")

    tool = server_module.build_search_tool("linux")

    description = tool.description or ""
    assert description.splitlines()[0] == "Universal file search tool for Linux"
    assert "Using locate with Unix-style search capabilities" in description
    assert 'locate -i "*.pdf"' in description
    assert "linux_params" in tool.input_schema["properties"]


def test_build_search_tool_darwin_describes_mdfind(on_platform):
    on_platform("Darwin")

    tool = server_module.build_search_tool("darwin")

    description = tool.description or ""
    assert description.splitlines()[0] == "Universal file search tool for Darwin"
    assert (
        "Using mdfind (Spotlight) with native macOS search capabilities" in description
    )
    assert "kMDItemDisplayName" in description
    assert "mac_params" in tool.input_schema["properties"]


def test_build_search_tool_unknown_platform_says_unknown(on_platform):
    on_platform("SunOS")

    tool = server_module.build_search_tool("sunos")

    assert "Unknown platform" in (tool.description or "")
    assert "Platform-specific syntax guide not available" in (tool.description or "")


# --- parse_search_arguments ---


def test_parse_arguments_reads_base_dict_and_windows_params():
    # Act
    query = server_module.parse_search_arguments(
        {
            "base": {"query": "report", "max_results": 5},
            "windows_params": {"match_case": True, "sort_by": 6},
        }
    )

    # Assert
    assert (query.query, query.max_results) == ("report", 5)
    assert query.windows_params is not None
    assert query.windows_params.match_case is True
    assert query.windows_params.sort_by == 6


def test_parse_arguments_accepts_base_as_json_string():
    query = server_module.parse_search_arguments(
        {"base": json.dumps({"query": "notes", "max_results": 7})}
    )

    assert (query.query, query.max_results) == ("notes", 7)


def test_parse_arguments_treats_non_json_base_string_as_query():
    query = server_module.parse_search_arguments({"base": "*.py"})

    assert query.query == "*.py"
    assert query.max_results == 100


def test_parse_arguments_accepts_windows_params_as_json_string():
    query = server_module.parse_search_arguments(
        {"base": {"query": "x"}, "windows_params": '{"sort_by": 13}'}
    )

    assert query.windows_params is not None
    assert query.windows_params.sort_by == 13


def test_parse_arguments_rejects_invalid_windows_params_json():
    with pytest.raises(ValueError, match="windows_params"):
        server_module.parse_search_arguments(
            {"base": {"query": "x"}, "windows_params": "{not json"}
        )


def test_parse_arguments_rejects_base_of_wrong_type():
    with pytest.raises(ValueError, match="base"):
        server_module.parse_search_arguments({"base": 42})


def test_parse_arguments_without_query_raises_validation_error():
    with pytest.raises(ValidationError):
        server_module.parse_search_arguments(None)


def test_parse_arguments_reads_mac_and_linux_params_issue_30():
    query = server_module.parse_search_arguments(
        {
            "base": {"query": "x"},
            "linux_params": {"regex_search": True},
            "mac_params": '{"search_directory": "/Users/me"}',
        }
    )

    assert query.linux_params is not None and query.linux_params.regex_search is True
    assert (
        query.mac_params is not None
        and query.mac_params.search_directory == "/Users/me"
    )


@pytest.mark.parametrize("key", ["mac_params", "linux_params"])
def test_parse_arguments_rejects_invalid_platform_params_json(key):
    with pytest.raises(ValueError, match=key):
        server_module.parse_search_arguments({"base": {"query": "x"}, key: "{not json"})


# --- format_results ---


def test_format_results_renders_every_field_with_na_for_missing_dates():
    assert server_module.format_results([REPORT]) == REPORT_TEXT


def test_format_results_omits_extension_suffix_when_absent():
    result = SearchResult(
        path="/tmp/Makefile", filename="Makefile", extension=None, size=10
    )

    text = server_module.format_results([result])

    assert text.splitlines()[1] == "Filename: Makefile"


def test_format_results_joins_multiple_results_with_newline():
    text = server_module.format_results([REPORT, REPORT])

    assert text == REPORT_TEXT + "\n" + REPORT_TEXT


def test_format_results_empty_list_is_empty_text():
    assert server_module.format_results([]) == ""


# --- create_server over a real MCP client session ---


@pytest.mark.anyio
async def test_server_lists_single_search_tool_with_platform_schema(on_platform):
    # Arrange
    on_platform("Windows")
    server = server_module.create_server(FakeSearchProvider(), "windows")

    # Act
    async with Client(server) as client:
        tools = (await client.list_tools()).tools

    # Assert
    assert [t.name for t in tools] == ["search"]
    assert tools[0].input_schema == UnifiedSearchQuery.get_schema_for_platform()


@pytest.mark.anyio
async def test_server_windows_search_passes_windows_params_and_returns_text(
    on_platform,
):
    # Arrange
    on_platform("Windows")
    provider = FakeSearchProvider(results=[REPORT])
    server = server_module.create_server(provider, "windows")

    # Act
    async with Client(server) as client:
        result = await client.call_tool(
            "search",
            {
                "base": {"query": "report", "max_results": 3},
                "windows_params": {"sort_by": 6, "match_path": True},
            },
        )

    # Assert
    assert result.is_error is False
    assert _text(result) == REPORT_TEXT
    assert provider.calls == [
        {
            "query": "report",
            "max_results": 3,
            "match_path": True,
            "match_case": False,
            "match_whole_word": False,
            "match_regex": False,
            "sort_by": 6,
        }
    ]


@pytest.mark.anyio
async def test_server_windows_search_without_windows_params_uses_defaults(on_platform):
    on_platform("Windows")
    provider = FakeSearchProvider()
    server = server_module.create_server(provider, "windows")

    async with Client(server) as client:
        await client.call_tool("search", {"base": {"query": "x"}})

    assert provider.calls[0]["sort_by"] == 1
    assert provider.calls[0]["match_path"] is False


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("platform_name", "system"), [("Linux", "linux"), ("Darwin", "darwin")]
)
async def test_server_command_line_search_passes_only_query_and_max_results(
    on_platform, platform_name, system
):
    on_platform(platform_name)
    provider = FakeSearchProvider()
    server = server_module.create_server(provider, system)

    async with Client(server) as client:
        result = await client.call_tool(
            "search", {"base": {"query": "*.py", "max_results": 9}}
        )

    assert result.is_error is False
    assert provider.calls == [{"query": "*.py", "max_results": 9}]


@pytest.mark.anyio
async def test_server_search_path_follows_system_argument(on_platform):
    # Arrange: the system argument, not the ambient platform, selects the provider call
    on_platform("Linux")
    provider = FakeSearchProvider()
    server = server_module.create_server(provider, "windows")

    # Act
    async with Client(server) as client:
        await client.call_tool(
            "search", {"base": {"query": "x"}, "windows_params": {"sort_by": 5}}
        )

    # Assert
    assert provider.calls[0]["sort_by"] == 5


@pytest.mark.anyio
async def test_server_darwin_search_passes_mac_params_issue_25(on_platform):
    on_platform("Darwin")
    provider = FakeSearchProvider()
    server = server_module.create_server(provider, "darwin")

    async with Client(server) as client:
        await client.call_tool(
            "search",
            {"base": {"query": "ENABLE"}, "mac_params": {"search_directory": "/repo"}},
        )

    assert provider.calls == [
        {
            "query": "ENABLE",
            "max_results": 100,
            "search_directory": "/repo",
            "live_updates": False,
            "literal_query": False,
            "interpret_query": False,
        }
    ]


@pytest.mark.anyio
async def test_server_linux_search_passes_linux_params_issue_30(on_platform):
    on_platform("Linux")
    provider = FakeSearchProvider()
    server = server_module.create_server(provider, "linux")

    async with Client(server) as client:
        await client.call_tool(
            "search", {"base": {"query": "x"}, "linux_params": {"regex_search": True}}
        )

    assert provider.calls == [
        {
            "query": "x",
            "max_results": 100,
            "ignore_case": True,
            "regex_search": True,
            "existing_files": True,
        }
    ]


@pytest.mark.anyio
async def test_server_linux_count_only_returns_match_count(on_platform):
    # Arrange
    on_platform("Linux")
    provider = FakeSearchProvider()
    server = server_module.create_server(provider, "linux")

    # Act
    async with Client(server) as client:
        result = await client.call_tool(
            "search", {"base": {"query": "x"}, "linux_params": {"count_only": True}}
        )

    # Assert
    assert result.is_error is False
    assert _text(result) == "Total matches: 70"
    assert provider.calls == [
        {
            "count": "x",
            "ignore_case": True,
            "regex_search": False,
            "existing_files": True,
        }
    ]


@pytest.mark.anyio
async def test_server_reports_mac_live_updates_as_tool_error(on_platform):
    on_platform("Darwin")
    runner_calls: List[List[str]] = []

    def runner(cmd: List[str]) -> "subprocess.CompletedProcess[str]":
        runner_calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    server = server_module.create_server(
        MacSearchProvider(run_command=runner), "darwin"
    )

    async with Client(server) as client:
        result = await client.call_tool(
            "search", {"base": {"query": "x"}, "mac_params": {"live_updates": True}}
        )

    assert result.is_error is True
    assert "live_updates" in _text(result)
    assert runner_calls == []


@pytest.mark.anyio
async def test_server_reports_missing_arguments_as_tool_error(on_platform):
    on_platform("Windows")
    provider = FakeSearchProvider()
    server = server_module.create_server(provider, "windows")

    async with Client(server) as client:
        result = await client.call_tool("search", None)

    assert result.is_error is True
    assert _text(result).startswith("Search failed:")
    assert provider.calls == []


@pytest.mark.anyio
async def test_server_reports_provider_failure_as_tool_error(on_platform):
    on_platform("Windows")
    server = server_module.create_server(
        FakeSearchProvider(error=RuntimeError("Everything is not running")), "windows"
    )

    async with Client(server) as client:
        result = await client.call_tool("search", {"base": {"query": "x"}})

    assert result.is_error is True
    assert _text(result) == "Search failed: Everything is not running"


@pytest.mark.anyio
async def test_server_reports_invalid_arguments_as_tool_error(on_platform):
    on_platform("Windows")
    provider = FakeSearchProvider()
    server = server_module.create_server(provider, "windows")

    async with Client(server) as client:
        result = await client.call_tool("search", {"base": {"max_results": 5}})

    assert result.is_error is True
    assert _text(result).startswith("Search failed:")
    assert provider.calls == []


@pytest.mark.anyio
async def test_server_rejects_unknown_tool_with_invalid_params_error(on_platform):
    on_platform("Windows")
    server = server_module.create_server(FakeSearchProvider(), "windows")

    async with Client(server) as client:
        with pytest.raises(MCPError) as excinfo:
            await client.call_tool("delete_everything", {})

    assert excinfo.value.error.code == -32602


@pytest.mark.anyio
async def test_server_exposes_no_resources_templates_or_prompts(on_platform):
    on_platform("Windows")
    server = server_module.create_server(FakeSearchProvider(), "windows")

    async with Client(server) as client:
        resources = (await client.list_resources()).resources
        templates = (await client.list_resource_templates()).resource_templates
        prompts = (await client.list_prompts()).prompts

    assert (resources, templates, prompts) == ([], [], [])


# --- entry points ---


def test_configure_windows_console_is_noop_off_windows(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(sys, "platform", "linux")
    stdout_before = sys.stdout

    server_module.configure_windows_console()

    assert sys.stdout is stdout_before


def test_main_exits_with_status_1_when_serve_fails(monkeypatch: pytest.MonkeyPatch):
    # Arrange
    async def failing_serve() -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(server_module, "serve", failing_serve)
    monkeypatch.setattr(server_module, "configure_windows_console", lambda: None)

    # Act
    with pytest.raises(SystemExit) as excinfo:
        server_module.main()

    # Assert
    assert excinfo.value.code == 1


@pytest.mark.anyio
async def test_serve_runs_platform_provider_over_stdio(
    on_platform, monkeypatch: pytest.MonkeyPatch
):
    # Arrange: the stdio transport and provider factory are the composition-root seams
    on_platform("Linux")
    provider = FakeSearchProvider(results=[REPORT])
    monkeypatch.setattr(
        SearchProvider, "get_provider", classmethod(lambda cls: provider)
    )

    async with create_client_server_memory_streams() as (
        client_streams,
        server_streams,
    ):

        @asynccontextmanager
        async def in_memory_stdio():
            yield server_streams

        monkeypatch.setattr(server_module, "stdio_server", in_memory_stdio)

        tools: List[Any] = []
        result: Any = None

        # Act
        with anyio.fail_after(10):
            async with anyio.create_task_group() as tg:
                tg.start_soon(server_module.serve)
                async with ClientSession(*client_streams) as session:
                    await session.initialize()
                    tools = (await session.list_tools()).tools
                    result = await session.call_tool(
                        "search", {"base": {"query": "report"}}
                    )
                tg.cancel_scope.cancel()

    # Assert
    assert [t.name for t in tools] == ["search"]
    assert "linux_params" in tools[0].input_schema["properties"]
    assert "Using locate with Unix-style search capabilities" in (
        tools[0].description or ""
    )
    assert _text(result) == REPORT_TEXT
    assert provider.calls == [{"query": "report", "max_results": 100}]


# --- configurable tool name (EVERYTHING_SEARCH_TOOL_NAME) ---


@pytest.mark.parametrize(
    ("value", "expected"),
    [(None, "search"), ("", "search"), ("everything_search", "everything_search")],
)
def test_resolve_tool_name_defaults_to_search(value, expected):
    assert server_module.resolve_tool_name(value) == expected


@pytest.mark.parametrize("value", ["bad name", "search!", "x" * 65, "search\n"])
def test_resolve_tool_name_rejects_names_clients_cannot_use(value):
    with pytest.raises(ValueError, match="EVERYTHING_SEARCH_TOOL_NAME"):
        server_module.resolve_tool_name(value)


def test_build_search_tool_uses_given_tool_name(on_platform):
    on_platform("Windows")

    tool = server_module.build_search_tool("windows", tool_name="everything_search")

    assert tool.name == "everything_search"


@pytest.mark.anyio
async def test_server_with_custom_tool_name_lists_and_answers_under_that_name(
    on_platform,
):
    # Arrange
    on_platform("Windows")
    provider = FakeSearchProvider(results=[REPORT])
    server = server_module.create_server(
        provider, "windows", tool_name="everything_search"
    )

    # Act
    async with Client(server) as client:
        names = [t.name for t in (await client.list_tools()).tools]
        result = await client.call_tool(
            "everything_search", {"base": {"query": "report"}}
        )
        with pytest.raises(MCPError) as excinfo:
            await client.call_tool("search", {"base": {"query": "report"}})

    # Assert
    assert names == ["everything_search"]
    assert _text(result) == REPORT_TEXT
    assert excinfo.value.error.code == -32602


@pytest.mark.anyio
async def test_serve_uses_tool_name_from_environment(
    on_platform, monkeypatch: pytest.MonkeyPatch
):
    # Arrange
    on_platform("Linux")
    monkeypatch.setenv("EVERYTHING_SEARCH_TOOL_NAME", "everything_search")
    provider = FakeSearchProvider()
    monkeypatch.setattr(
        SearchProvider, "get_provider", classmethod(lambda cls: provider)
    )
    names: List[str] = []

    async with create_client_server_memory_streams() as (
        client_streams,
        server_streams,
    ):

        @asynccontextmanager
        async def in_memory_stdio():
            yield server_streams

        monkeypatch.setattr(server_module, "stdio_server", in_memory_stdio)

        # Act
        with anyio.fail_after(10):
            async with anyio.create_task_group() as tg:
                tg.start_soon(server_module.serve)
                async with ClientSession(*client_streams) as session:
                    await session.initialize()
                    names = [t.name for t in (await session.list_tools()).tools]
                tg.cancel_scope.cancel()

    # Assert
    assert names == ["everything_search"]


def test_main_exits_with_status_1_for_invalid_tool_name(
    monkeypatch: pytest.MonkeyPatch, caplog
):
    # Arrange: fail if the server gets as far as opening stdio
    @asynccontextmanager
    async def must_not_open_stdio():
        raise AssertionError("stdio opened despite an invalid tool name")
        yield  # pragma: no cover

    monkeypatch.setenv("EVERYTHING_SEARCH_TOOL_NAME", "not valid!")
    monkeypatch.setattr(server_module, "configure_windows_console", lambda: None)
    monkeypatch.setattr(server_module, "stdio_server", must_not_open_stdio)
    monkeypatch.setattr(
        SearchProvider, "get_provider", classmethod(lambda cls: FakeSearchProvider())
    )

    # Act
    with pytest.raises(SystemExit) as excinfo:
        server_module.main()

    # Assert
    assert excinfo.value.code == 1
    assert "EVERYTHING_SEARCH_TOOL_NAME" in caplog.text
    assert "stdio opened" not in caplog.text
