# Changelog

All notable changes to this project are documented here.

## 0.3.2 - 2026-10-17

### Added

- Published to the official [MCP Registry](https://registry.modelcontextprotocol.io/) as `io.github.mamertofabian/mcp-everything-search` (`server.json`). Directories that import from the registry (such as PulseMCP and Glama) pick it up from there.

No code changes since 0.3.1.

## 0.3.1 - 2026-10-17

This release borrows fixes from community forks: more robust Windows results, hardened search commands, and an optional tool name.

### Fixed

- **Windows: one bad attribute no longer drops a result** (#14). Each timestamp is converted separately, so a file with an unrepresentable date is still returned (with that date as `N/A`). Thanks @amcaude and @WhizZest, and @s-github-2 and @gjy1992, who wrote the same fix in their forks.
- **Windows: unreadable results are reported.** If some matches cannot be read from Everything, the readable ones are returned and the output ends with a warning giving the count; if none can be read, the search fails with an error instead of returning nothing.
- Clear errors when the Everything SDK DLL cannot be loaded, naming `EVERYTHING_SDK_PATH`.
- Search commands (`mdfind`, `locate`) time out after 30 seconds instead of hanging the server.
- A query starting with `-` is no longer passed to `locate` as an option (the query now follows `--`), and a literal or interpreted `mdfind` query starting with `-` is rejected.
- macOS `search_directory` expands `~` and must exist, instead of silently returning no results.

The three hardening fixes above come from @amcaude's fork.

### Added

- `EVERYTHING_SEARCH_TOOL_NAME` renames the tool (default `search`) for clients where the generic name collides with another server's tool (#19). The name may use letters, digits, `_` and `-` (1-64 characters); an invalid value stops the server at startup. Thanks @kshin5.

### Changed

- **Windows: `EVERYTHING_SDK_PATH` is now required.** The server no longer falls back to a hard-coded `D:\dev\tools\...` path; if the variable is unset or does not point to a file, it stops at startup with an error naming the variable.
- Diagnostics go through Python logging (stderr) instead of `Debug:` prints.

### Development

- `everything_sdk.py` is now fully tested (with a fake DLL, so on every OS) and included in the CI lint/type checks; `search_interface.py` tests were extended.
- Python 3.11, 3.12 and 3.13 classifiers added.

## 0.3.0 - 2026-10-17

This release restores a working install and fixes the Windows `sort_by` schema. It requires mcp 2.x.

### Fixed

- **Server failed to start with mcp 2.x.** v0.2.1 allowed any `mcp>=1.0.0`, and mcp 2.0 removed the decorator API it used, so fresh installs crashed with `AttributeError: 'Server' object has no attribute 'list_resources'`. The server now uses the mcp 2.x lowlevel API.
- **Windows: `sort_by` broke the tool schema** (#16, #26). The schema referenced `#/$defs/WindowsSortOption` from inside `windows_params`, so strict clients (Cherry Studio, DeepSeek) failed with `PointerToNowhere`. With mcp 1.30, the server itself also returned `PointerToNowhere` for any call that set `sort_by` (reproduced on Windows 11). The enum is now inlined as an integer enum. Thanks @plmelancon (#37), @WhizZest (#29), @mj520 (#18) and @fcyl0801 (#16) for the analysis and fixes.
- Every schema property now declares a `type`, which should stop Gemini CLI from skipping the tool with "missing types in its parameter schema" (#21). Not yet confirmed with Gemini CLI.
- **Non-ASCII queries returned no results** on Windows systems with a non-UTF-8 locale (#27). mcp 2.x reads stdin as UTF-8. Thanks @WhizZest (#28) for the diagnosis.
- `SyntaxWarning: invalid escape sequence` on import with Python 3.12+. Thanks @beibeiyhj (#11).
- **macOS and Linux platform parameters were ignored** (#25, #30). `mac_params.search_directory` now scopes `mdfind` with `-onlyin`, `literal_query`/`interpret_query` pass the query to Spotlight as-is, and `linux_params` (`ignore_case`, `regex_search`, `existing_files`, `count_only`) map to `locate` options. `live_updates` returns an error because `mdfind -live` never exits. Adapted from #32, thanks @WhizZest.

### Changed

- **Requires `mcp>=2.0.0,<3`.**
- Failed searches (invalid arguments, Everything not running, etc.) now return a tool result with `isError: true` and the message `Search failed: ...`, instead of a normal-looking text result.
- Calling an unknown tool name returns a JSON-RPC invalid-params error (-32602).
- Linux searches now apply the documented `linux_params` defaults even when `linux_params` is omitted: case-insensitive (`-i`) and existing files only (`-e`), limited to `max_results` (`-l`).

### Documentation

- README now documents the real argument structure (`base` plus the platform's `windows_params`, `mac_params` or `linux_params`), with examples that validate against the tool schema (#19), the full result fields, and the error result.

### Development

- Tests for the tool schema, argument parsing, result formatting and the MCP server, run in CI on Windows, macOS and Linux with Python 3.10 and 3.13.
- Development follows MAID manifests (`manifests/`).

## 0.2.1 - 2024-12-19

- Cross-platform support: macOS (`mdfind`) and Linux (`locate`/`plocate`) in addition to Windows (Everything SDK).

## 0.1.2 - 2024-12-16

- Search syntax documentation and README updates.

## 0.1.0 - 2024-12-15

- Initial release: Windows file search through the Everything SDK.
