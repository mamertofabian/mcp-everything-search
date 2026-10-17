"""MCP server implementation for cross-platform file search."""

import json
import os
import re
import platform
import sys
from typing import Any, Dict, List, Optional

from mcp import MCPError
from mcp.server import Server, ServerRequestContext
from mcp.server.stdio import stdio_server
from mcp.types import (
    INVALID_PARAMS,
    CallToolRequestParams,
    CallToolResult,
    ListPromptsResult,
    ListResourcesResult,
    ListResourceTemplatesResult,
    ListToolsResult,
    PaginatedRequestParams,
    TextContent,
    Tool,
)

from pydantic import BaseModel

from .platform_search import UnifiedSearchQuery, WindowsSpecificParams
from .search_interface import PartialResults, SearchProvider, SearchResult

_DEFAULT_TOOL_NAME = "search"
_TOOL_NAME_ENV = "EVERYTHING_SEARCH_TOOL_NAME"
# Strictest common client limit (e.g. Anthropic tool names): letters, digits, "_" and "-", 1-64 chars
_TOOL_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

_PLATFORM_INFO = {
    "windows": "Using Everything SDK with full search capabilities",
    "darwin": "Using mdfind (Spotlight) with native macOS search capabilities",
    "linux": "Using locate with Unix-style search capabilities",
}

_SYNTAX_DOCS = {
    "darwin": r"""macOS Spotlight (mdfind) Search Syntax:
                
Basic Usage:
- Simple text search: Just type the words you're looking for
- Phrase search: Use quotes ("exact phrase")
- Filename search: -name "filename"
- Directory scope: -onlyin /path/to/dir

Special Parameters:
- Live updates: -live
- Literal search: -literal
- Interpreted search: -interpret

Metadata Attributes:
- kMDItemDisplayName
- kMDItemTextContent
- kMDItemKind
- kMDItemFSSize
- And many more OS X metadata attributes""",
    "linux": r"""Linux Locate Search Syntax:

Basic Usage:
- Simple pattern: locate filename
- Case-insensitive: -i pattern
- Regular expressions: -r pattern
- Existing files only: -e pattern
- Count matches: -c pattern

Pattern Wildcards:
- * matches any characters
- ? matches single character
- [] matches character classes

Examples:
- locate -i "*.pdf"
- locate -r "/home/.*\.txt$"
- locate -c "*.doc"
""",
    "windows": r"""Search for files and folders using Everything SDK.
                
Features:
- Fast file and folder search across all indexed drives
- Support for wildcards and boolean operators
- Multiple sort options (name, path, size, dates)
- Case-sensitive and whole word matching
- Regular expression support
- Path matching
Search Syntax Guide:
1. Basic Operators:
   - space: AND operator
   - |: OR operator
   - !: NOT operator
   - < >: Grouping
   - " ": Search for an exact phrase
2. Wildcards:
   - *: Matches zero or more characters
   - ?: Matches exactly one character
   Note: Wildcards match the whole filename by default. Disable Match whole filename to match wildcards anywhere.
3. Functions:
   Size and Count:
   - size:<size>[kb|mb|gb]: Search by file size
   - count:<max>: Limit number of results
   - childcount:<count>: Folders with specific number of children
   - childfilecount:<count>: Folders with specific number of files
   - childfoldercount:<count>: Folders with specific number of subfolders
   - len:<length>: Match filename length
   Dates:
   - datemodified:<date>, dm:<date>: Modified date
   - dateaccessed:<date>, da:<date>: Access date
   - datecreated:<date>, dc:<date>: Creation date
   - daterun:<date>, dr:<date>: Last run date
   - recentchange:<date>, rc:<date>: Recently changed date
   
   Date formats: YYYY[-MM[-DD[Thh[:mm[:ss[.sss]]]]]] or today, yesterday, lastweek, etc.
   
   File Attributes and Types:
   - attrib:<attributes>, attributes:<attributes>: Search by file attributes (A:Archive, H:Hidden, S:System, etc.)
   - type:<type>: Search by file type
   - ext:<list>: Search by semicolon-separated extensions
   
   Path and Name:
   - path:<path>: Search in specific path
   - parent:<path>, infolder:<path>, nosubfolders:<path>: Search in path excluding subfolders
   - startwith:<text>: Files starting with text
   - endwith:<text>: Files ending with text
   - child:<filename>: Folders containing specific child
   - depth:<count>, parents:<count>: Files at specific folder depth
   - root: Files with no parent folder
   - shell:<name>: Search in known shell folders
   Duplicates and Lists:
   - dupe, namepartdupe, attribdupe, dadupe, dcdupe, dmdupe, sizedupe: Find duplicates
   - filelist:<list>: Search pipe-separated (|) file list
   - filelistfilename:<filename>: Search files from list file
   - frn:<frnlist>: Search by File Reference Numbers
   - fsi:<index>: Search by file system index
   - empty: Find empty folders
4. Function Syntax:
   - function:value: Equal to value
   - function:<=value: Less than or equal
   - function:<value: Less than
   - function:=value: Equal to
   - function:>value: Greater than
   - function:>=value: Greater than or equal
   - function:start..end: Range of values
   - function:start-end: Range of values
5. Modifiers:
   - case:, nocase:: Enable/disable case sensitivity
   - file:, folder:: Match only files or folders
   - path:, nopath:: Match full path or filename only
   - regex:, noregex:: Enable/disable regex
   - wfn:, nowfn:: Match whole filename or anywhere
   - wholeword:, ww:: Match whole words only
   - wildcards:, nowildcards:: Enable/disable wildcards
Examples:
1. Find Python files modified today:
   ext:py datemodified:today
2. Find large video files:
   ext:mp4|mkv|avi size:>1gb
3. Find files in specific folder:
   path:C:\Projects *.js
""",
}


def resolve_tool_name(value: Optional[str]) -> str:
    """Return the configured tool name, or "search" when unset; reject names clients cannot use."""
    if not value:
        return _DEFAULT_TOOL_NAME
    if not _TOOL_NAME_PATTERN.fullmatch(value):
        raise ValueError(
            f"Invalid {_TOOL_NAME_ENV} {value!r}: use 1-64 letters, digits, '_' or '-'"
        )
    return value


def build_search_tool(system: str, tool_name: str = _DEFAULT_TOOL_NAME) -> Tool:
    """Return the search tool with platform-specific documentation and schema."""
    description = f"""Universal file search tool for {platform.system()}

Current Implementation:
{_PLATFORM_INFO.get(system, "Unknown platform")}

Search Syntax Guide:
{_SYNTAX_DOCS.get(system, "Platform-specific syntax guide not available")}
"""
    return Tool(
        name=tool_name,
        description=description,
        input_schema=UnifiedSearchQuery.get_schema_for_platform(),
    )


def _platform_params(arguments: Dict[str, Any], key: str) -> Dict[str, Any]:
    value = arguments[key]
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON in {key}")
    if isinstance(value, dict):
        return value
    raise ValueError(f"'{key}' must be a string or dictionary")


def parse_search_arguments(arguments: Optional[Dict[str, Any]]) -> UnifiedSearchQuery:
    """Parse tool arguments into a validated query.

    mcp 2.x does not validate arguments against the input schema, so this is
    the validation boundary. ``base`` may be a dict, a JSON string, or a plain
    query string; ``windows_params`` may be a dict or a JSON string.
    """
    arguments = arguments or {}
    base_params: Dict[str, Any] = {}
    windows_params: Dict[str, Any] = {}

    if "base" in arguments:
        if isinstance(arguments["base"], str):
            try:
                base_params = json.loads(arguments["base"])
            except json.JSONDecodeError:
                # If not valid JSON string, treat as simple query string
                base_params = {"query": arguments["base"]}
        elif isinstance(arguments["base"], dict):
            base_params = arguments["base"]
        else:
            raise ValueError("'base' parameter must be a string or dictionary")

    if "windows_params" in arguments:
        windows_params = _platform_params(arguments, "windows_params")
    platform_params = {
        key: _platform_params(arguments, key)
        for key in ("mac_params", "linux_params")
        if key in arguments
    }

    return UnifiedSearchQuery(
        **{**base_params, "windows_params": windows_params, **platform_params}
    )


def format_results(results: List[SearchResult]) -> str:
    """Render search results as the tool's text output, warning about unreadable matches."""
    text = "\n".join(
        [
            f"Path: {r.path}\n"
            f"Filename: {r.filename}"
            f"{f' ({r.extension})' if r.extension else ''}\n"
            f"Size: {r.size:,} bytes\n"
            f"Created: {r.created if r.created else 'N/A'}\n"
            f"Modified: {r.modified if r.modified else 'N/A'}\n"
            f"Accessed: {r.accessed if r.accessed else 'N/A'}\n"
            for r in results
        ]
    )
    if isinstance(results, PartialResults) and results.unreadable:
        text += (
            f"\nWarning: {results.unreadable} matching result(s) could not be read and were omitted. "
            "See the server log."
        )
    return text


def _search_text(
    search_provider: SearchProvider, system: str, query: UnifiedSearchQuery
) -> str:
    if system == "windows":
        # Use Everything SDK directly
        windows_params = query.windows_params or WindowsSpecificParams()
        options: Dict[str, Any] = windows_params.model_dump()
        return format_results(
            search_provider.search_files(
                query=query.query, max_results=query.max_results, **options
            )
        )

    if system == "linux" and query.linux_params and query.linux_params.count_only:
        options = query.linux_params.model_dump(exclude={"count_only"})
        return f"Total matches: {search_provider.count_files(query.query, **options)}"

    # Use command-line tools (mdfind/locate)
    platform_params: Optional[BaseModel] = None
    if system == "darwin":
        platform_params = query.mac_params
    elif system == "linux":
        platform_params = query.linux_params
    options = (
        platform_params.model_dump(exclude={"count_only"}) if platform_params else {}
    )
    return format_results(
        search_provider.search_files(
            query=query.query, max_results=query.max_results, **options
        )
    )


def create_server(
    search_provider: SearchProvider, system: str, tool_name: str = _DEFAULT_TOOL_NAME
) -> Server:
    """Build the lowlevel mcp 2.x server bound to a provider and lowercase platform name."""

    async def on_list_tools(
        ctx: ServerRequestContext, params: Optional[PaginatedRequestParams]
    ) -> ListToolsResult:
        return ListToolsResult(tools=[build_search_tool(system, tool_name)])

    async def on_call_tool(
        ctx: ServerRequestContext, params: CallToolRequestParams
    ) -> CallToolResult:
        if params.name != tool_name:
            raise MCPError(INVALID_PARAMS, f"Unknown tool: {params.name}")
        try:
            query = parse_search_arguments(params.arguments)
            text = _search_text(search_provider, system, query)
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Search failed: {str(e)}")],
                is_error=True,
            )
        return CallToolResult(
            content=[TextContent(type="text", text=text)],
            is_error=False,
        )

    async def on_list_resources(
        ctx: ServerRequestContext, params: Optional[PaginatedRequestParams]
    ) -> ListResourcesResult:
        return ListResourcesResult(resources=[])

    async def on_list_resource_templates(
        ctx: ServerRequestContext, params: Optional[PaginatedRequestParams]
    ) -> ListResourceTemplatesResult:
        return ListResourceTemplatesResult(resource_templates=[])

    async def on_list_prompts(
        ctx: ServerRequestContext, params: Optional[PaginatedRequestParams]
    ) -> ListPromptsResult:
        return ListPromptsResult(prompts=[])

    return Server(
        "universal-search",
        on_list_tools=on_list_tools,
        on_call_tool=on_call_tool,
        on_list_resources=on_list_resources,
        on_list_resource_templates=on_list_resource_templates,
        on_list_prompts=on_list_prompts,
    )


async def serve() -> None:
    """Run the server over stdio with the current platform's search provider."""
    tool_name = resolve_tool_name(os.environ.get(_TOOL_NAME_ENV))
    server = create_server(
        SearchProvider.get_provider(), platform.system().lower(), tool_name
    )
    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options, raise_exceptions=True)


def configure_windows_console() -> None:
    """Configure Windows console for UTF-8 output."""
    import ctypes

    if sys.platform == "win32":
        # Enable virtual terminal processing
        kernel32 = ctypes.windll.kernel32
        STD_OUTPUT_HANDLE = -11
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004

        handle = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
        mode = ctypes.c_ulong()
        kernel32.GetConsoleMode(handle, ctypes.byref(mode))
        mode.value |= ENABLE_VIRTUAL_TERMINAL_PROCESSING
        kernel32.SetConsoleMode(handle, mode)

        # Set UTF-8 encoding for console output
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")


def main() -> None:
    """Main entry point."""
    import asyncio
    import logging

    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    configure_windows_console()

    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        logging.info("Server stopped by user")
        sys.exit(0)
    except Exception as e:
        logging.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)
