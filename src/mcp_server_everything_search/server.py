"""MCP server implementation for cross-platform file search."""

import platform
import sys
from typing import List
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool, Resource, ResourceTemplate, Prompt
from pydantic import BaseModel, Field

from .platform_search import UnifiedSearchQuery, WindowsSpecificParams, build_search_command
from .search_interface import SearchProvider

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
    current_platform = platform.system().lower()
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
        """Return the search tool with platform-specific documentation and schema."""
        platform_info = {
            'windows': "Using Everything SDK with full search capabilities",
            'darwin': "Using mdfind (Spotlight) with native macOS search capabilities",
            'linux': "Using locate with Unix-style search capabilities"
        }

        syntax_docs = {
            'darwin': """macOS Spotlight (mdfind) Search Syntax:
                
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

            'linux': """Linux Locate Search Syntax:

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
            'windows': """Everything Search Syntax:

Operators:
- space: AND operator
- | (pipe): OR operator
- ! (exclamation): NOT operator
- < > (angle brackets): Grouping
- " " (quotes): Exact phrase

Functions:
- size:<size>[kb|mb|gb]
- date:<date> (YYYY[-MM[-DD[THH[:MM[:SS]]]]])
- attrib:<attribute>
- type:<type>
- ext:<ext1;ext2>

Special Keywords:
- file: Match files only
- folder: Match folders only
- duplicates: Find duplicate files
- empty: Find empty folders

Examples:
- "project report" ext:pdf
- size:>1gb type:video
- modified:today !temp
"""
        }

        description = f"""Universal file search tool for {platform.system()}

Current Implementation:
{platform_info.get(current_platform, "Unknown platform")}

Search Syntax Guide:
{syntax_docs.get(current_platform, "Platform-specific syntax guide not available")}
"""

        return [
            Tool(
                name="search",
                description=description,
                inputSchema=UnifiedSearchQuery.get_schema_for_platform()
            )
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> List[TextContent]:
        if name != "search":
            raise ValueError(f"Unknown tool: {name}")

        try:
            # Parse and handle both inputs
            import json

            try:
                # Parse base input
                if isinstance(arguments.get('base'), str):
                    try:
                        base_params = json.loads(arguments['base'])
                    except json.JSONDecodeError:
                        # If not valid JSON, treat as simple query string
                        base_params = {'query': arguments['base']}
                else:
                    base_params = arguments.get('base', {})

                # Parse windows_params if present
                if arguments.get('windows_params'):
                    try:
                        windows_params = json.loads(arguments['windows_params'])
                    except json.JSONDecodeError:
                        windows_params = {}
                else:
                    windows_params = {}

                # Combine parameters
                query_params = {
                    **base_params,
                    'windows_params': windows_params
                }

                # Create unified query
                query = UnifiedSearchQuery(**query_params)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in parameters: {e}")

            if current_platform == "windows":
                # Use Everything SDK directly
                platform_params = query.windows_params or WindowsSpecificParams()
                results = search_provider.search_files(
                    query=query.query,
                    max_results=query.max_results,
                    match_path=platform_params.match_path,
                    match_case=platform_params.match_case,
                    match_whole_word=platform_params.match_whole_word,
                    match_regex=platform_params.match_regex,
                    sort_by=platform_params.sort_by
                )
            else:
                # Use command-line tools (mdfind/locate)
                cmd = build_search_command(query)
                results = search_provider.search_files(
                    command=cmd,
                    max_results=query.base.max_results
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
