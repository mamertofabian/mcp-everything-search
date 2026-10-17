# Changelog

All notable changes to this project are documented here.

## 0.3.0 - unreleased

This release restores a working install and fixes the Windows `sort_by` schema. It requires mcp 2.x.

### Fixed

- **Server failed to start with mcp 2.x.** v0.2.1 allowed any `mcp>=1.0.0`, and mcp 2.0 removed the decorator API it used, so fresh installs crashed with `AttributeError: 'Server' object has no attribute 'list_resources'`. The server now uses the mcp 2.x lowlevel API.
- **Windows: `sort_by` broke the tool schema** (#16, #26). The schema referenced `#/$defs/WindowsSortOption` from inside `windows_params`, so strict clients (Cherry Studio, DeepSeek) failed with `PointerToNowhere`. With mcp 1.30, the server itself also returned `PointerToNowhere` for any call that set `sort_by` (reproduced on Windows 11). The enum is now inlined as an integer enum. Thanks @plmelancon (#37), @WhizZest (#29), @mj520 (#18) and @fcyl0801 (#16) for the analysis and fixes.
- Every schema property now declares a `type`, which should stop Gemini CLI from skipping the tool with "missing types in its parameter schema" (#21). Not yet confirmed with Gemini CLI.
- **Non-ASCII queries returned no results** on Windows systems with a non-UTF-8 locale (#27). mcp 2.x reads stdin as UTF-8. Thanks @WhizZest (#28) for the diagnosis.
- `SyntaxWarning: invalid escape sequence` on import with Python 3.12+. Thanks @beibeiyhj (#11).

### Changed

- **Requires `mcp>=2.0.0,<3`.**
- Failed searches (invalid arguments, Everything not running, etc.) now return a tool result with `isError: true` and the message `Search failed: ...`, instead of a normal-looking text result.
- Calling an unknown tool name returns a JSON-RPC invalid-params error (-32602).

### Documentation

- README now documents the real argument structure (`base` plus `windows_params`), with examples that validate against the tool schema (#19), the full result fields, and the error result.

### Development

- Tests for the tool schema, argument parsing, result formatting and the MCP server, run in CI on Windows, macOS and Linux with Python 3.10 and 3.13.
- Development follows MAID manifests (`manifests/`).

## 0.2.1 - 2024-12-19

- Cross-platform support: macOS (`mdfind`) and Linux (`locate`/`plocate`) in addition to Windows (Everything SDK).

## 0.1.2 - 2024-12-16

- Search syntax documentation and README updates.

## 0.1.0 - 2024-12-15

- Initial release: Windows file search through the Everything SDK.
