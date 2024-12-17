# Everything Search MCP Server

An MCP server that provides fast file searching capabilities using the Everything SDK.

## Tools

### search

Search for files and folders using Everything SDK.

Parameters:
- `query` (required): Search query string. Supports wildcards (* and ?) and more. See the search syntax guide for more details.
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
<details>
<summary>Advanced Search Queries</summary>

### Basic Operators
- `space`: AND operator
- `|`: OR operator
- `!`: NOT operator
- `< >`: Grouping
- `" "`: Search for an exact phrase

### Wildcards
- `*`: Matches zero or more characters
- `?`: Matches exactly one character

Note: Wildcards match the whole filename by default. Disable Match whole filename to match wildcards anywhere.

### Functions

#### Size and Count
- `size:<size>[kb|mb|gb]`: Search by file size
- `count:<max>`: Limit number of results
- `childcount:<count>`: Folders with specific number of children
- `childfilecount:<count>`: Folders with specific number of files
- `childfoldercount:<count>`: Folders with specific number of subfolders
- `len:<length>`: Match filename length

#### Dates
- `datemodified:<date>, dm:<date>`: Modified date
- `dateaccessed:<date>, da:<date>`: Access date
- `datecreated:<date>, dc:<date>`: Creation date
- `daterun:<date>, dr:<date>`: Last run date
- `recentchange:<date>, rc:<date>`: Recently changed date

Date formats: YYYY[-MM[-DD[Thh[:mm[:ss[.sss]]]]]] or today, yesterday, lastweek, etc.

#### File Attributes and Types
- `attrib:<attributes>, attributes:<attributes>`: Search by file attributes (A:Archive, H:Hidden, S:System, etc.)
- `type:<type>`: Search by file type
- `ext:<list>`: Search by semicolon-separated extensions

#### Path and Name
- `path:<path>`: Search in specific path
- `parent:<path>, infolder:<path>, nosubfolders:<path>`: Search in path excluding subfolders
- `startwith:<text>`: Files starting with text
- `endwith:<text>`: Files ending with text
- `child:<filename>`: Folders containing specific child
- `depth:<count>, parents:<count>`: Files at specific folder depth
- `root`: Files with no parent folder
- `shell:<name>`: Search in known shell folders

#### Duplicates and Lists
- `dupe, namepartdupe, attribdupe, dadupe, dcdupe, dmdupe, sizedupe`: Find duplicates
- `filelist:<list>`: Search pipe-separated (|) file list
- `filelistfilename:<filename>`: Search files from list file
- `frn:<frnlist>`: Search by File Reference Numbers
- `fsi:<index>`: Search by file system index
- `empty`: Find empty folders

### Function Syntax

- `function:value`: Equal to value
- `function:<=value`: Less than or equal
- `function:<value`: Less than
- `function:=value`: Equal to
- `function:>value`: Greater than
- `function:>=value`: Greater than or equal
- `function:start..end`: Range of values
- `function:start-end`: Range of values

### Modifiers

- `case:, nocase:: Enable/disable case sensitivity
- `file:, folder:: Match only files or folders
- `path:, nopath:: Match full path or filename only
- `regex:, noregex:: Enable/disable regex
- `wfn:, nowfn:: Match whole filename or anywhere
- `wholeword:, ww:: Match whole words only
- `wildcards:, nowildcards:: Enable/disable wildcards

### Examples

1. Find Python files modified today:
   `ext:py datemodified:today`

2. Find large video files:
   `ext:mp4|mkv|avi size:>1gb`

3. Find files in specific folder:
   `path:C:\Projects *.js`

</details>

## Prerequisites

1. Windows operating system (required - this server only works on Windows)
2. [Everything](https://www.voidtools.com/) search utility:
   - Download and install from https://www.voidtools.com/
   - **Make sure the Everything service is running**
3. Everything SDK:
   - Download from https://www.voidtools.com/support/everything/sdk/
   - Extract the SDK files to a location on your system

## Installation

### Using uv (recommended)

When using [`uv`](https://docs.astral.sh/uv/) no specific installation is needed. We will
use [`uvx`](https://docs.astral.sh/uv/guides/tools/) to directly run *mcp-server-everything-search*.

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

The server requires the Everything SDK DLL to be available:

Environment variable:
   ```
   EVERYTHING_SDK_PATH=path\to\Everything-SDK\dll\Everything64.dll
   ```

### Usage with Claude Desktop

Add this to your `claude_desktop_config.json`:

<details>
<summary>Using uvx</summary>

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
<summary>Using pip installation</summary>

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

Using PowerShell, running `Get-Content -Path "$env:APPDATA\Claude\logs\mcp*.log" -Tail 20 -Wait` will show the logs from the server and may help you debug any issues.

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
