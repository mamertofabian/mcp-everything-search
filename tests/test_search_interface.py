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


def test_default_command_timeout_is_30_seconds():
    from mcp_server_everything_search.search_interface import SEARCH_TIMEOUT_SECONDS

    assert SEARCH_TIMEOUT_SECONDS == 30.0


def test_run_command_uses_default_timeout_when_none_given():
    import inspect

    from mcp_server_everything_search.search_interface import (
        SEARCH_TIMEOUT_SECONDS,
        run_command,
    )

    assert (
        inspect.signature(run_command).parameters["timeout"].default
        == SEARCH_TIMEOUT_SECONDS
    )


def test_run_command_times_out_with_clear_error():
    from mcp_server_everything_search.search_interface import run_command

    with pytest.raises(RuntimeError, match="timed out after 0.2 seconds"):
        run_command([sys.executable, "-c", "import time; time.sleep(5)"], timeout=0.2)


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
        WindowsSearchProvider,
        "__init__",
        lambda self, everything_sdk=None, dll_path=None: None,
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


def test_mac_search_directory_scopes_search_issue_25(tmp_path: Path):
    runner = FakeRunner()

    MacSearchProvider(run_command=runner).search_files(
        "ENABLE", search_directory=str(tmp_path)
    )

    assert runner.commands == [["mdfind", "-onlyin", str(tmp_path), "-name", "ENABLE"]]


def test_mac_search_directory_expands_home(tmp_path: Path, monkeypatch):
    (tmp_path / "sub").mkdir()
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    runner = FakeRunner()

    MacSearchProvider(run_command=runner).search_files("x", search_directory="~/sub")

    [cmd] = runner.commands
    # Compare as paths: expanduser keeps "/" on Windows ("C:\\...\\tmp/sub")
    assert cmd[:2] == ["mdfind", "-onlyin"]
    assert Path(cmd[2]) == tmp_path / "sub"
    assert cmd[3:] == ["-name", "x"]


def test_mac_missing_search_directory_is_rejected(tmp_path: Path):
    runner = FakeRunner()

    with pytest.raises(ValueError, match="does not exist"):
        MacSearchProvider(run_command=runner).search_files(
            "x", search_directory=str(tmp_path / "missing")
        )

    assert runner.commands == []


@pytest.mark.parametrize("option", ["literal_query", "interpret_query"])
def test_mac_raw_query_starting_with_dash_is_rejected(option):
    # A leading "-" would be parsed as an mdfind option (e.g. "-live" never exits)
    runner = FakeRunner()
    options: Dict[str, Any] = {option: True}

    with pytest.raises(ValueError, match="must not start with '-'"):
        MacSearchProvider(run_command=runner).search_files("-live", **options)

    assert runner.commands == []


def test_mac_filename_query_starting_with_dash_is_passed_as_name_value():
    runner = FakeRunner()

    MacSearchProvider(run_command=runner).search_files("-draft")

    assert runner.commands == [["mdfind", "-name", "-draft"]]


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


def test_mac_scoped_literal_query_orders_directory_then_flags(tmp_path: Path):
    runner = FakeRunner()

    MacSearchProvider(run_command=runner).search_files(
        "q", search_directory=str(tmp_path), literal_query=True, interpret_query=True
    )

    assert runner.commands == [
        ["mdfind", "-onlyin", str(tmp_path), "-literal", "-interpret", "q"]
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
    assert runner.commands[-1] == ["plocate", "-i", "-e", "-l", "2", "--", "bashrc"]
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

    assert runner.commands[-1] == ["plocate", "-r", "-l", "5", "--", "^/etc"]


def test_linux_query_starting_with_dash_is_searched_not_parsed_as_option():
    runner = FakeRunner()

    _linux(runner).search_files("--database=/etc/shadow")

    assert runner.commands[-1][-2:] == ["--", "--database=/etc/shadow"]


def test_linux_regex_uses_long_option_for_mlocate():
    runner = FakeRunner(
        {"which plocate": _done(returncode=1), "which locate": _done("/usr/bin/locate")}
    )
    provider = _linux(runner)

    provider.search_files("x", regex_search=True)

    assert runner.commands[-1] == [
        "locate",
        "-i",
        "--regex",
        "-e",
        "-l",
        "100",
        "--",
        "x",
    ]


def test_linux_count_files_returns_match_count():
    # Arrange
    runner = FakeRunner({"plocate": _done("70\n")})
    provider = _linux(runner)

    # Act
    count = provider.count_files("bashrc", ignore_case=True, existing_files=True)

    # Assert
    assert count == 70
    assert runner.commands[-1] == ["plocate", "-i", "-e", "-c", "--", "bashrc"]


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


@pytest.mark.parametrize("dll_path", [None, ""])
def test_windows_provider_requires_a_non_empty_sdk_path(dll_path):
    with pytest.raises(RuntimeError, match="EVERYTHING_SDK_PATH is not set"):
        WindowsSearchProvider(dll_path=dll_path)


def test_windows_provider_rejects_missing_dll_file(tmp_path: Path):
    with pytest.raises(RuntimeError, match="does not exist"):
        WindowsSearchProvider(dll_path=str(tmp_path / "Everything64.dll"))


def test_windows_provider_rejects_a_directory_as_dll_path(tmp_path: Path):
    with pytest.raises(RuntimeError, match="does not exist"):
        WindowsSearchProvider(dll_path=str(tmp_path))


def test_windows_provider_loads_sdk_from_existing_dll_path(tmp_path: Path, monkeypatch):
    # Arrange: replace the SDK class so no real DLL is loaded
    from mcp_server_everything_search import everything_sdk

    dll = tmp_path / "Everything64.dll"
    dll.write_bytes(b"MZ")
    loaded: List[str] = []

    class RecordingSDK(FakeEverythingSDK):
        def __init__(self, dll_path: str) -> None:
            super().__init__()
            loaded.append(dll_path)

    monkeypatch.setattr(everything_sdk, "EverythingSDK", RecordingSDK)

    # Act
    provider = WindowsSearchProvider(dll_path=str(dll))

    # Assert
    assert loaded == [str(dll)]
    assert isinstance(provider.everything_sdk, RecordingSDK)


def test_get_provider_passes_everything_sdk_path_to_windows_provider(monkeypatch):
    # Arrange: the factory is the composition root that reads the environment
    received: Dict[str, Any] = {}

    def capture(self, everything_sdk=None, dll_path=None):
        received["dll_path"] = dll_path

    monkeypatch.setattr(platform, "system", lambda: "Windows")
    monkeypatch.setenv("EVERYTHING_SDK_PATH", r"C:\sdk\Everything64.dll")
    monkeypatch.setattr(WindowsSearchProvider, "__init__", capture)

    # Act
    SearchProvider.get_provider()

    # Assert
    assert received == {"dll_path": r"C:\sdk\Everything64.dll"}
