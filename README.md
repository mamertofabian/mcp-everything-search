# Everything Search MCP Server

[![smithery badge](https://smithery.ai/badge/mcp-server-everything-search)](https://smithery.ai/server/mcp-server-everything-search)

An MCP server that provides fast file searching capabilities across Windows, macOS, and Linux. On Windows, it uses the [Everything](https://www.voidtools.com/) SDK. On macOS, it uses the built-in `mdfind` command. On Linux, it uses the `locate`/`plocate` command.

## Tools

### search

Search for files and folders across your system. The search capabilities and syntax support vary by platform:

- Windows: Full Everything SDK features (see syntax guide below)
- macOS: Basic filename and content search using Spotlight database
- Linux: Basic filename search using locate database

Parameters:

- `query` (required): Search query string. See platform-specific notes below.
- `max_results` (optional): Maximum number of results to return (default: 100, max: 1000)
- `match_path` (optional): Match against full path instead of filename only (default: false)
- `match_case` (optional): Enable case-sensitive search (default: false)
- `match_whole_word` (optional): Match whole words only (default: false)
- `match_regex` (optional): Enable regex search (default: false)
- `sort_by` (optional): Sort order for results (default: 1). Available options:

```
  - 1: Sort by filename (A to Z)
  - 2: Sort by filename (Z to A)
  - 3: Sort by path (A to Z)
  - 4: Sort by path (Z to A)
  - 5: Sort by size (smallest first)
  - 6: Sort by size (largest first)
  - 7: Sort by extension (A to Z)
  - 8: Sort by extension (Z to A)
  - 11: Sort by creation date (oldest first)
  - 12: Sort by creation date (newest first)
  - 13: Sort by modification date (oldest first)
  - 14: Sort by modification date (newest first)
```

Examples:

```json
{
  "query": "*.py",
  "max_results": 50,
  "sort_by": 6
}
```

```json
{
  "query": "ext:py datemodified:today",
  "max_results": 10
}
```

Response includes:

- File/folder path
- File size in bytes
- Last modified date

### Search Syntax Guide

For detailed information about the search syntax supported on each platform (Windows, macOS, and Linux), please see [SEARCH_SYNTAX.md](SEARCH_SYNTAX.md).

## Prerequisites

### Windows

1. [Everything](https://www.voidtools.com/) search utility:
   - Download and install from https://www.voidtools.com/
   - **Make sure the Everything service is running**
2. Everything SDK:
   - Download from https://www.voidtools.com/support/everything/sdk/
   - Extract the SDK files to a location on your system

### Linux

1. Install and initialize the `locate` or `plocate` command:
   - Ubuntu/Debian: `sudo apt-get install plocate` or `sudo apt-get install mlocate`
   - Fedora: `sudo dnf install mlocate`
2. After installation, update the database:
   - For plocate: `sudo updatedb`
   - For mlocate: `sudo /etc/cron.daily/mlocate`

### macOS

No additional setup required. The server uses the built-in `mdfind` command.

## Installation

### Installing via Smithery

To install Everything Search for Claude Desktop automatically via [Smithery](https://smithery.ai/server/mcp-server-everything-search):

```bash
npx -y @smithery/cli install mcp-server-everything-search --client claude
```

### Using uv (recommended)

When using [`uv`](https://docs.astral.sh/uv/) no specific installation is needed. We will
use [`uvx`](https://docs.astral.sh/uv/guides/tools/) to directly run _mcp-server-everything-search_.

### Using PIP

Alternatively you can install `mcp-server-everything-search` via pip:

```
pip install mcp-server-everything-search
```

After installation, you can run it as a script using:

```
python -m mcp_server_everything_search
```

## Configuration

### Windows

The server requires the Everything SDK DLL to be available:

Environment variable:

```
EVERYTHING_SDK_PATH=path\to\Everything-SDK\dll\Everything64.dll
```

### Linux and macOS

No additional configuration required.

### Usage with Claude Desktop

Add one of these configurations to your `claude_desktop_config.json` based on your platform:

<details>
<summary>Windows (using uvx)</summary>

```json
"mcpServers": {
  "everything-search": {
    "command": "uvx",
    "args": ["mcp-server-everything-search"],
    "env": {
      "EVERYTHING_SDK_PATH": "path/to/Everything-SDK/dll/Everything64.dll"
    }
  }
}
```

</details>

<details>
<summary>Windows (using pip installation)</summary>

```json
"mcpServers": {
  "everything-search": {
    "command": "python",
    "args": ["-m", "mcp_server_everything_search"],
    "env": {
      "EVERYTHING_SDK_PATH": "path/to/Everything-SDK/dll/Everything64.dll"
    }
  }
}
```

</details>

<details>
<summary>Linux and macOS</summary>

```json
"mcpServers": {
  "everything-search": {
    "command": "uvx",
    "args": ["mcp-server-everything-search"]
  }
}
```

Or if using pip installation:

```json
"mcpServers": {
  "everything-search": {
    "command": "python",
    "args": ["-m", "mcp_server_everything_search"]
  }
}
```

</details>

## Debugging

You can use the MCP inspector to debug the server. For uvx installations:

```
npx @modelcontextprotocol/inspector uvx mcp-server-everything-search
```

Or if you've installed the package in a specific directory or are developing on it:

```
git clone https://github.com/mamertofabian/mcp-everything-search.git
cd mcp-everything-search/src/mcp_server_everything_search
npx @modelcontextprotocol/inspector uv run mcp-server-everything-search
```

To view server logs:

Linux/macOS:

```bash
tail -f ~/.config/Claude/logs/mcp*.log
```

Windows (PowerShell):

```powershell
Get-Content -Path "$env:APPDATA\Claude\logs\mcp*.log" -Tail 20 -Wait
```

## Development

If you are doing local development, there are two ways to test your changes:

1. Run the MCP inspector to test your changes. See [Debugging](#debugging) for run instructions.

2. Test using the Claude desktop app. Add the following to your `claude_desktop_config.json`:

```json
"everything-search": {
  "command": "uv",
  "args": [
    "--directory",
    "/path/to/mcp-everything-search/src/mcp_server_everything_search",
    "run",
    "mcp-server-everything-search"
  ],
  "env": {
    "EVERYTHING_SDK_PATH": "path/to/Everything-SDK/dll/Everything64.dll"
  }
}
```

## License

This MCP server is licensed under the MIT License. This means you are free to use, modify, and distribute the software, subject to the terms and conditions of the MIT License. For more details, please see the LICENSE file in the project repository.

## Disclaimer

This project is not affiliated with, endorsed by, or sponsored by voidtools (the creators of Everything search utility). This is an independent project that utilizes the publicly available Everything SDK.
