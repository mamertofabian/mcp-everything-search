"""MCP server implementation for cross-platform file search."""

import platform
import ctypes
import sys
from typing import List
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool, Resource, ResourceTemplate, Prompt
from pydantic import BaseModel, Field

from .search_interface import SearchProvider, SearchResult

class SearchQuery(BaseModel):
    """Model for search query parameters."""
    query: str = Field(
        description="Search query string. See the search syntax guide for details."
    )
    max_results: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of results to return (1-1000)"
    )
    match_path: bool = Field(
        default=False,
        description="Match against full path instead of filename only"
    )
    match_case: bool = Field(
        default=False,
        description="Enable case-sensitive search"
    )
    match_whole_word: bool = Field(
        default=False,
        description="Match whole words only"
    )
    match_regex: bool = Field(
        default=False,
        description="Enable regex search"
    )
    sort_by: int = Field(
        default=1,
        description="Sort order for results (Note: Not all sort options available on all platforms)"
    )

async def serve() -> None:
    """Run the server."""
    search_provider = SearchProvider.get_provider()
    
    server = Server("universal-search")

    @server.list_resources()
    async def list_resources() -> list[Resource]:
        """Return an empty list since this server doesn't provide any resources."""
        return []

    @server.list_resource_templates()
    async def list_resource_templates() -> list[ResourceTemplate]:
        """Return an empty list since this server doesn't provide any resource templates."""
        return []

    @server.list_prompts()
    async def list_prompts() -> list[Prompt]:
        """Return an empty list since this server doesn't provide any prompts."""
        return []

    @server.list_tools()
    async def list_tools() -> List[Tool]:
        """Return the universal search tool with platform-specific documentation."""
        search_docs = {
            'windows': """Search using Everything SDK.
Features:
- Fast file and folder search across all indexed drives
- Support for wildcards and boolean operators
- Multiple sort options
- Case-sensitive and whole word matching
- Regular expression support""",
            
            'darwin': """Search using macOS Spotlight (mdfind).
Features:
- Real-time file indexing
- Basic name and content search
- Case-insensitive by default
- Limited regex support""",
            
            'linux': """Search using locate database.
Features:
- Fast filename-based search
- Case-insensitive option
- Basic regex support
- Note: Database updates periodically (usually daily)"""
        }

        return [
            Tool(
                name="search",
                description=f"Universal file search tool\n\n{search_docs.get(platform.system().lower(), 'Platform-specific search')}",
                inputSchema=SearchQuery.model_json_schema(),
            )
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> List[TextContent]:
        if name != "search":
            raise ValueError(f"Unknown tool: {name}")

        try:
            query = SearchQuery(**arguments)
            results = search_provider.search_files(
                query=query.query,
                max_results=query.max_results,
                match_path=query.match_path,
                match_case=query.match_case,
                match_whole_word=query.match_whole_word,
                match_regex=query.match_regex,
                sort_by=query.sort_by
            )
            
            return [TextContent(
                type="text",
                text="\n".join([
                    f"Path: {r.path}\n"
                    f"Filename: {r.filename}"
                    f"{f' ({r.extension})' if r.extension else ''}\n"
                    f"Size: {r.size:,} bytes\n"
                    f"Created: {r.created if r.created else 'N/A'}\n"
                    f"Modified: {r.modified if r.modified else 'N/A'}\n"
                    f"Accessed: {r.accessed if r.accessed else 'N/A'}\n"
                    for r in results
                ])
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Search failed: {str(e)}"
            )]

    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options, raise_exceptions=True)

def configure_windows_console():
    """Configure Windows console for UTF-8 output."""
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
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')

def main() -> None:
    """Main entry point."""
    import asyncio
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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
