# Everything Search MCP Server

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

<details>
<summary>Platform-Specific Search Features</summary>

## Windows Search (Everything SDK)

The following advanced search features are only available on Windows when using the Everything SDK:

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

- `case:, nocase:`: Enable/disable case sensitivity
- `file:, folder:`: Match only files or folders
- `path:, nopath:`: Match full path or filename only
- `regex:, noregex:`: Enable/disable regex
- `wfn:, nowfn:`: Match whole filename or anywhere
- `wholeword:, ww:`: Match whole words only
- `wildcards:, nowildcards:`: Enable/disable wildcards

### Examples

1. Find Python files modified today:
   `ext:py datemodified:today`

2. Find large video files:
   `ext:mp4|mkv|avi size:>1gb`

3. Find files in specific folder:
   `path:C:\Projects *.js`

## macOS Search (mdfind)

macOS uses Spotlight's metadata search capabilities through the `mdfind` command. The following features are supported:

### Command Options

- `-live`: Provides live updates to search results as files change
- `-count`: Show only the number of matches
- `-onlyin directory`: Limit search to specific directory
- `-literal`: Treat query as literal text without interpretation
- `-interpret`: Interpret query as if typed in Spotlight menu

### Basic Search

- Simple text search looks for matches in any metadata attribute
- Wildcards (`*`) are supported in search strings
- Multiple words are treated as AND conditions
- Whitespace is significant in queries
- Use parentheses () to group expressions

### Search Operators

- `|` (OR): Match either word, e.g., `"image|photo"`
- `-` (NOT): Exclude matches, e.g., `-screenshot`
- `=`, `==` (equal)
- `!=` (not equal)
- `<`, `>` (less/greater than)
- `<=`, `>=` (less/greater than or equal)

### Value Comparison Modifiers

Use brackets with these modifiers:

- `[c]`: Case-insensitive comparison
- `[d]`: Diacritical marks insensitive
- Can be combined, e.g., `[cd]` for both

### Content Types (kind:)

- `application`, `app`: Applications
- `audio`, `music`: Audio/Music files
- `bookmark`: Bookmarks
- `contact`: Contacts
- `email`, `mail message`: Email messages
- `event`: Calendar events
- `folder`: Folders
- `font`: Fonts
- `image`: Images
- `movie`: Movies
- `pdf`: PDF documents
- `preferences`: System preferences
- `presentation`: Presentations
- `todo`: Calendar to-dos

### Date Filters (date:)

Time-based search using these keywords:

- `today`, `yesterday`, `tomorrow`
- `this week`, `next week`
- `this month`, `next month`
- `this year`, `next year`

Or use time functions:

- `$time.today()`
- `$time.yesterday()`
- `$time.this_week()`
- `$time.this_month()`
- `$time.this_year()`
- `$time.tomorrow()`
- `$time.next_week()`
- `$time.next_month()`
- `$time.next_year()`

### Common Metadata Attributes

Search specific metadata using these attributes:

- `kMDItemAuthors`: Document authors
- `kMDItemContentType`: File type
- `kMDItemContentTypeTree`: File type hierarchy
- `kMDItemCreator`: Creating application
- `kMDItemDescription`: File description
- `kMDItemDisplayName`: Display name
- `kMDItemFSContentChangeDate`: File modification date
- `kMDItemFSCreationDate`: File creation date
- `kMDItemFSName`: Filename
- `kMDItemKeywords`: Keywords/tags
- `kMDItemLastUsedDate`: Last used date
- `kMDItemNumberOfPages`: Page count
- `kMDItemTitle`: Document title
- `kMDItemUserTags`: User-assigned tags

### Examples

1. Find images modified yesterday:
   `kind:image date:yesterday`

2. Find documents by author (case-insensitive):
   `kMDItemAuthors ==[c] "John Doe"`

3. Find files in specific directory:
   `mdfind -onlyin ~/Documents "query"`

4. Find files by tag:
   `kMDItemUserTags = "Important"`

5. Find files created by application:
   `kMDItemCreator = "Pixelmator*"`

6. Find PDFs with specific text:
   `kind:pdf "search term"`

7. Find recent presentations:
   `kind:presentation date:this week`

8. Count matching files:
   `mdfind -count "kind:image date:today"`

9. Monitor for new matches:
   `mdfind -live "kind:pdf"`

10. Complex metadata search:
    `kMDItemContentTypeTree = "public.image" && kMDItemUserTags = "vacation" && kMDItemFSContentChangeDate >= $time.this_month()`

Note: Use `mdls filename` to see all available metadata attributes for a specific file.

## Linux Search (locate/plocate)

Linux uses the locate/plocate command for fast filename searching. The following features are supported:

### Basic Search

- Simple text search matches against filenames
- Multiple words are treated as AND conditions
- Wildcards (`*` and `?`) are supported
- Case-insensitive by default

### Search Options

- `-i`: Case-insensitive search (default)
- `-c`: Count matches instead of showing them
- `-r` or `--regex`: Use regular expressions
- `-b`: Match only the basename
- `-w`: Match whole words only

### Examples

1. Find all Python files:
   `*.py`

2. Find files in home directory:
   `/home/username/*`

3. Case-sensitive search for specific file:
   `--regex "^/etc/[A-Z].*\.conf$"`

4. Count matching files:
   Use with `-c` parameter

Note: The locate database must be up to date for accurate results. Run `sudo updatedb` to update the database manually.

</details>

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
