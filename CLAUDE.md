# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an MCP (Model Context Protocol) server that provides cross-platform file search capabilities:
- **Windows**: Uses the Everything SDK for fast indexed search
- **macOS**: Uses `mdfind` (Spotlight) for native search
- **Linux**: Uses `locate`/`plocate` for filesystem search

The server exposes a single `search` tool with platform-specific parameter schemas and syntax support.

## Development Commands

### Testing and Running

```bash
# Run the server with MCP inspector for testing
npx @modelcontextprotocol/inspector uv run mcp-server-everything-search

# Run directly with uv
uv run mcp-server-everything-search

# Run as Python module (after pip install)
python -m mcp_server_everything_search
```

### Code Quality

```bash
# Type checking
uv run pyright

# Linting
uv run ruff check

# Formatting
uv run ruff format

# Run tests
uv run pytest
```

### Building

```bash
# Build the package
uv build
```

## Architecture

### Core Components

1. **server.py** - Main MCP server implementation
   - Defines the `search` tool with platform-specific schemas
   - Handles parameter parsing and validation using Pydantic
   - Routes search requests to appropriate platform provider
   - Returns formatted search results as TextContent

2. **search_interface.py** - Abstract search provider interface
   - `SearchProvider`: Abstract base class defining the search contract
   - `WindowsSearchProvider`: Everything SDK wrapper
   - `MacSearchProvider`: mdfind command wrapper
   - `LinuxSearchProvider`: locate/plocate command wrapper
   - `SearchResult`: Universal dataclass for all platforms

3. **platform_search.py** - Platform-specific parameter models
   - `BaseSearchQuery`: Common search parameters (query, max_results)
   - `WindowsSpecificParams`: Everything SDK options (match_path, match_case, etc.)
   - `MacSpecificParams`: mdfind options (live_updates, search_directory, etc.)
   - `LinuxSpecificParams`: locate options (ignore_case, regex_search, etc.)
   - `UnifiedSearchQuery`: Combines all parameter models with platform-aware schema generation
   - `build_search_command()`: Builds platform-specific command arrays

4. **everything_sdk.py** - Windows Everything SDK wrapper
   - `EverythingSDK`: ctypes wrapper for Everything64.dll
   - Comprehensive constant definitions for request flags and sort options
   - Windows filetime to Python datetime conversion
   - Full error handling with custom EverythingError exception

### Key Design Patterns

- **Strategy Pattern**: Platform-specific search providers implementing common SearchProvider interface
- **Factory Pattern**: `SearchProvider.get_provider()` returns the correct provider based on platform.system()
- **Adapter Pattern**: Each provider adapts platform-specific tools to unified SearchResult format

### Platform-Specific Notes

**Windows**:
- Requires `EVERYTHING_SDK_PATH` environment variable pointing to Everything64.dll
- Uses ctypes to call SDK functions directly (no subprocess calls)
- Supports full Everything search syntax with advanced filters and sorting

**macOS**:
- Uses subprocess to call `mdfind` command
- No additional dependencies required (built-in)

**Linux**:
- Checks for `plocate` first, falls back to `locate`
- Provides detailed error messages if database not initialized
- Uses subprocess to call locate commands

### Parameter Flow

1. Client sends search request with platform-specific parameters
2. `server.py` parses `base` and platform-specific params (e.g., `windows_params`)
3. Creates `UnifiedSearchQuery` from combined parameters
4. Routes to appropriate `SearchProvider` based on `platform.system()`
5. Provider executes search and returns list of `SearchResult` objects
6. Server formats results as TextContent with file details

## Environment Variables

- `EVERYTHING_SDK_PATH` (Windows only): Path to Everything64.dll (default: `D:\dev\tools\Everything-SDK\dll\Everything64.dll`)

## Installation Methods

The server supports three installation methods:
1. **Smithery CLI**: `npx -y @smithery/cli install mcp-server-everything-search --client claude`
2. **uv (recommended)**: Use `uvx mcp-server-everything-search`
3. **pip**: `pip install mcp-server-everything-search` then `python -m mcp_server_everything_search`

## MAID Workflow

This repository uses MAID (Manifest-driven AI Development). The installed MAID skills in `.claude/skills/` and `.codex/skills/` are the authoritative workflow.

Run MAID through the repo wrapper, which needs only `uv`:

```bash
scripts/maid <command>    # wraps: uvx --from "maid-runner[all]@latest" maid
```

maid-runner is not a project dependency, so read `uv run maid ...` in the generated MAID Runner section below as `scripts/maid ...`.

Per change: `maid-planner` -> behavioral tests (red) -> `scripts/maid validate --mode behavioral` -> approval -> `scripts/maid plan lock <manifest>` -> `scripts/maid manifest promote <draft>` -> implement -> `scripts/maid validate --mode implementation` -> `scripts/maid verify --profile handoff --summary` -> implementation review -> `outcome:` + `scripts/maid learn`.

<!-- BEGIN MAID RUNNER -->
## MAID Runner

Instruction payload version: 2026.09.18.1

### MAID Skills Workflow
Use the installed MAID skills for manifest-driven development: `maid-planner`, `maid-plan-review`, `maid-implement-draft`, `maid-implementer`, `maid-implementation-review`, `maid-evolver`, `maid-auditor`, `maid-incident-logger`, `maid-outcome-enrich`, `maid-run-review`.

For new features, bug fixes, and refactors, plan with `maid-planner`, review with `maid-plan-review`, implement with `maid-implementer`, and review the result with `maid-implementation-review` before handoff. When continuing from `manifests/drafts/*.manifest.yaml`, use `maid-implement-draft` to harden, lock, promote, implement, review, and capture Outcome.

Before treating a file's language as unsupported, run `maid validators` and install a matching validator plugin when available instead of skipping MAID for that file.

Draft manifests under `manifests/drafts/` are planning inventory, not active contracts. Child implementation drafts live at `manifests/drafts/*.manifest.yaml`; epic planning records live at `manifests/drafts/*.epic.yaml` and use split-before-promote before implementation; archived draft records are historical inventory. Before promoting the selected child draft, refresh the Outcome index when needed and run `uv run maid recall --for-manifest manifests/drafts/<slug>.manifest.yaml --plan-packet` when completed Outcome records exist. Recall is advisory planning context only: it can inform draft hardening and implementation risks, but it does not expand scope or replace red evidence, behavioral validation, plan lock, implementation validation, or review. Use `uv run maid insights` to review recurring Outcome lessons when an index is available. To intentionally include instructive failed or abandoned Outcome lessons, refresh the index with `uv run maid learn --include-status completed --include-status abandoned`, then recall from that index; the completed-only default is unchanged. When related Outcome evidence is retrieved, do not dump a raw recall or insights transcript into the task. Digest it visibly: name applicable lessons, reject stale or irrelevant lessons with a reason, and state what changed because of the evidence for the current planning, implementation, or review phase. Recalled, aggregated, and digested Outcomes remain advisory planning context only; they do not create an approval, promotion, done, or review gate. Promote one selected child draft with `uv run maid manifest promote manifests/drafts/<slug>.manifest.yaml`. Do not manually move or copy draft manifests. For metadata-only reference cleanup on locked active manifests, use `uv run maid plan revise <manifest> --reason "<text>" --preserve-red-evidence`. For review-driven behavioral contract changes while implementation is uncommitted, use `uv run maid plan revise <manifest> --reason "<text>" --stash-implementation` so MAID temporarily hides declared implementation changes while it captures fresh red evidence. This cannot hide committed implementation. If revised tests fail for missing behavior in committed code, plain `maid plan revise` can capture fresh red evidence before the fix. If they already pass and valid evidence cannot be preserved, report the evidence blocker and the pre-implementation baseline needed for recovery; do not reset shared history or bypass evidence requirements. See 'Revision Evidence After Implementation' in `docs/draft-manifest-workflow.md`. While a draft or promoted contract belongs to the current unmerged task, revise that same contract in place; use `maid plan revise` when it is locked. A contract is durable when accepted into shared project history, including integration or release branches regardless of name; a local task commit alone is not acceptance. Check repository policy and history, and clarify uncertain acceptance before rewriting. Use new manifests for genuinely separate work or evolution of durable contracts through chain merging or `maid-evolver` supersession.

Declare each touched source file in `files.create`, `files.edit`, `files.scope`, or `files.delete`; `files.read` is context, not writable scope. When public behavior changes in a touched file, add focused behavioral or characterization tests and declare any affected public artifacts in `files.create` or `files.edit`, even if the file was previously listed only in `files.scope`. Use `files.scope` for narrow no-artifact wiring covered by behavioral tests instead of forcing a whole-file public artifact snapshot.

Always capture an Outcome record after implementation validation and implementation review, before final handoff. Capture Outcome after implementation review so the result records the reviewed evidence. Outcome capture is required for completed, partial, failed, superseded, archived, or abandoned MAID work. The Outcome must cite concrete validation evidence and review notes; it does not replace behavioral tests, declared artifacts, validation commands, or implementation review. After Outcome capture, run `uv run maid learn` to refresh the local `.maid/outcomes.json` advisory index for subsequent recall. `.maid/outcomes.json` is generated and ignored; do not commit it. If `maid learn` fails, report the refresh failure as advisory unless recall or insights are required for the current task. See `docs/draft-manifest-workflow.md` and `docs/manifest-outcome-records.md`.

Available MAID agents: `maid-implementation-reviewer`.
<!-- END MAID RUNNER -->
