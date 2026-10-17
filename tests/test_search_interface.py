"""Behavioral tests for the platform search providers.

Commands are executed through an injected runner, so mdfind/locate are never
run; the Everything SDK is replaced by an in-memory fake.
"""

import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import pytest

from mcp_server_everything_search.search_interface import (
    LinuxSearchProvider,
    MacSearchProvider,
    SearchProvider,
    SearchResult,
    WindowsSearchProvider,
)


class FakeRunner:
    """Records commands and returns canned process results keyed by program."""

    def __init__(
        self, outputs: Optional[Dict[str, subprocess.CompletedProcess]] = None
    ):
        self.outputs = outputs or {}
        self.commands: List[List[str]] = []

    def __call__(self, cmd: List[str]) -> "subprocess.CompletedProcess[str]":
        self.commands.append(cmd)
        key = " ".join(cmd[:2]) if cmd[0] == "which" else cmd[0]
        return self.outputs.get(
            key, subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        )


def _done(
    stdout: str = "", returncode: int = 0, stderr: str = ""
) -> "subprocess.CompletedProcess[str]":
    return subprocess.CompletedProcess([], returncode, stdout=stdout, stderr=stderr)


def _linux(runner: FakeRunner) -> LinuxSearchProvider:
    return LinuxSearchProvider(run_command=runner)


class FakeEverythingSDK:
    def __init__(self) -> None:
        self.calls: List[Dict[str, Any]] = []

    def search_files(self, **kwargs: Any) -> List[Any]:
        self.calls.append(kwargs)
        return [SearchResult(path=r"C:\x\a.txt", filename="a.txt")]


# --- run_command ---


def test_run_command_captures_text_output_and_exit_code():
    # The one test that starts a real process: it covers the default runner itself.
    from mcp_server_everything_search.search_interface import run_command

    runner: Callable[[List[str]], "subprocess.CompletedProcess[str]"] = run_command

    result = runner([sys.executable, "-c", "import sys; print('hi'); sys.exit(3)"])

    assert (result.returncode, result.stdout.strip()) == (3, "hi")


# --- SearchProvider factory ---


@pytest.mark.parametrize(
    ("system", "expected"),
    [
        ("Darwin", MacSearchProvider),
        ("Linux", LinuxSearchProvider),
        ("Windows", WindowsSearchProvider),
    ],
)
def test_get_provider_returns_platform_provider(monkeypatch, system, expected):
    # Constructors probe the system (which / DLL); stub them to test the factory alone
    monkeypatch.setattr(platform, "system", lambda: system)
    monkeypatch.setattr(
        LinuxSearchProvider, "__init__", lambda self, run_command=None: None
    )
    monkeypatch.setattr(
        WindowsSearchProvider, "__init__", lambda self, everything_sdk=None: None
    )

    assert isinstance(SearchProvider.get_provider(), expected)


def test_get_provider_unsupported_platform_raises(monkeypatch):
    monkeypatch.setattr(platform, "system", lambda: "SunOS")

    with pytest.raises(NotImplementedError):
        SearchProvider.get_provider()


def test_count_files_is_unsupported_by_default():
    with pytest.raises(NotImplementedError, match="Linux"):
        MacSearchProvider(run_command=FakeRunner()).count_files("x")


# --- macOS (mdfind) ---


def test_mac_default_search_is_filename_search_limited_to_max_results():
    # Arrange
    runner = FakeRunner({"mdfind": _done("/a/one.txt\n/a/two.txt\n/a/three.txt\n")})

    # Act
    results = MacSearchProvider(run_command=runner).search_files("one", max_results=2)

    # Assert
    assert runner.commands == [["mdfind", "-name", "one"]]
    assert [r.path for r in results] == ["/a/one.txt", "/a/two.txt"]


def test_mac_search_directory_scopes_search_issue_25():
    runner = FakeRunner()

    MacSearchProvider(run_command=runner).search_files(
        "ENABLE", search_directory="/Users/me/repo"
    )

    assert runner.commands == [
        ["mdfind", "-onlyin", "/Users/me/repo", "-name", "ENABLE"]
    ]


@pytest.mark.parametrize(
    ("option", "flag"),
    [("literal_query", "-literal"), ("interpret_query", "-interpret")],
)
def test_mac_literal_or_interpret_passes_raw_query(option, flag):
    runner = FakeRunner()

    options: Dict[str, Any] = {option: True}

    MacSearchProvider(run_command=runner).search_files(
        'kMDItemKind == "PDF"', **options
    )

    assert runner.commands == [["mdfind", flag, 'kMDItemKind == "PDF"']]


def test_mac_scoped_literal_query_orders_directory_then_flags():
    runner = FakeRunner()

    MacSearchProvider(run_command=runner).search_files(
        "q", search_directory="/d", literal_query=True, interpret_query=True
    )

    assert runner.commands == [
        ["mdfind", "-onlyin", "/d", "-literal", "-interpret", "q"]
    ]


def test_mac_live_updates_is_rejected_because_mdfind_live_never_exits():
    runner = FakeRunner()

    with pytest.raises(ValueError, match="live_updates"):
        MacSearchProvider(run_command=runner).search_files("x", live_updates=True)

    assert runner.commands == []


def test_mac_mdfind_failure_raises_with_stderr():
    runner = FakeRunner({"mdfind": _done(returncode=1, stderr="boom")})

    with pytest.raises(RuntimeError, match="mdfind failed: boom"):
        MacSearchProvider(run_command=runner).search_files("x")


# --- Linux (locate/plocate) ---


def test_linux_prefers_plocate():
    runner = FakeRunner({"which plocate": _done("/usr/bin/plocate")})

    provider = _linux(runner)

    assert (provider.locate_cmd, provider.locate_type) == ("plocate", "plocate")


def test_linux_falls_back_to_locate():
    runner = FakeRunner(
        {"which plocate": _done(returncode=1), "which locate": _done("/usr/bin/locate")}
    )

    provider = _linux(runner)

    assert (provider.locate_cmd, provider.locate_type) == ("locate", "mlocate")


def test_linux_without_any_locate_raises_install_hint():
    runner = FakeRunner(
        {"which plocate": _done(returncode=1), "which locate": _done(returncode=1)}
    )

    with pytest.raises(RuntimeError, match="sudo apt-get install plocate"):
        _linux(runner)


def test_linux_default_search_ignores_case_existing_only_and_limits():
    # Arrange
    runner = FakeRunner({"plocate": _done("/etc/a\n/etc/b\n/etc/c\n")})
    provider = _linux(runner)

    # Act
    results = provider.search_files("bashrc", max_results=2)

    # Assert
    assert runner.commands[-1] == ["plocate", "-i", "-e", "-l", "2", "bashrc"]
    assert [r.path for r in results] == ["/etc/a", "/etc/b"]


def test_linux_params_map_to_locate_flags_issue_30():
    runner = FakeRunner()
    provider = _linux(runner)

    provider.search_files(
        "^/etc",
        max_results=5,
        ignore_case=False,
        regex_search=True,
        existing_files=False,
    )

    assert runner.commands[-1] == ["plocate", "-r", "-l", "5", "^/etc"]


def test_linux_regex_uses_long_option_for_mlocate():
    runner = FakeRunner(
        {"which plocate": _done(returncode=1), "which locate": _done("/usr/bin/locate")}
    )
    provider = _linux(runner)

    provider.search_files("x", regex_search=True)

    assert runner.commands[-1] == ["locate", "-i", "--regex", "-e", "-l", "100", "x"]


def test_linux_count_files_returns_match_count():
    # Arrange
    runner = FakeRunner({"plocate": _done("70\n")})
    provider = _linux(runner)

    # Act
    count = provider.count_files("bashrc", ignore_case=True, existing_files=True)

    # Assert
    assert count == 70
    assert runner.commands[-1] == ["plocate", "-i", "-e", "-c", "bashrc"]


def test_linux_count_files_with_unparseable_output_raises():
    runner = FakeRunner({"plocate": _done("not a number\n")})

    with pytest.raises(RuntimeError, match="count"):
        _linux(runner).count_files("x")


def test_linux_count_files_missing_database_raises_updatedb_hint():
    runner = FakeRunner(
        {"plocate": _done(returncode=1, stderr="plocate.db: No such file or directory")}
    )

    with pytest.raises(RuntimeError, match="sudo updatedb"):
        _linux(runner).count_files("x")


def test_linux_missing_database_raises_updatedb_hint():
    runner = FakeRunner(
        {
            "plocate": _done(
                returncode=1,
                stderr="/var/lib/plocate/plocate.db: No such file or directory",
            )
        }
    )

    with pytest.raises(RuntimeError, match="sudo updatedb"):
        _linux(runner).search_files("x")


def test_linux_other_failure_raises_with_stderr():
    runner = FakeRunner({"plocate": _done(returncode=1, stderr="permission denied")})

    with pytest.raises(RuntimeError, match="plocate failed: permission denied"):
        _linux(runner).search_files("x")


# --- result conversion ---


def test_existing_file_result_includes_stat_details(tmp_path: Path):
    # Arrange
    file = tmp_path / "report.pdf"
    file.write_bytes(b"12345")
    runner = FakeRunner({"plocate": _done(f"{file}\n")})

    # Act
    [result] = _linux(runner).search_files("report")

    # Assert
    assert (result.path, result.filename, result.extension, result.size) == (
        str(file),
        "report.pdf",
        "pdf",
        5,
    )
    assert isinstance(result.modified, datetime)


def test_inaccessible_path_result_has_basic_info_only():
    runner = FakeRunner({"plocate": _done("/nonexistent/dir/Makefile\n")})

    [result] = _linux(runner).search_files("Makefile")

    assert (
        result.path,
        result.filename,
        result.size,
        result.modified,
        result.attributes,
    ) == (
        "/nonexistent/dir/Makefile",
        "Makefile",
        None,
        None,
        None,
    )


# --- Windows (Everything SDK) ---


def test_windows_normalizes_slashes_and_forwards_options_to_sdk():
    # Arrange
    from mcp_server_everything_search.search_interface import EverythingBackend

    sdk = FakeEverythingSDK()
    assert isinstance(sdk, EverythingBackend)
    provider = WindowsSearchProvider(everything_sdk=sdk)

    # Act
    results = provider.search_files(
        "C:/Users\\\\me", max_results=7, match_case=True, sort_by=6
    )

    # Assert
    assert sdk.calls == [
        {
            "query": "C:\\Users\\me",
            "max_results": 7,
            "match_path": False,
            "match_case": True,
            "match_whole_word": False,
            "match_regex": False,
            "sort_by": 6,
        }
    ]
    assert [r.filename for r in results] == ["a.txt"]


def test_windows_without_sort_by_uses_everything_name_ascending_default():
    sdk = FakeEverythingSDK()

    WindowsSearchProvider(everything_sdk=sdk).search_files("x")

    assert sdk.calls[0]["sort_by"] == 1
