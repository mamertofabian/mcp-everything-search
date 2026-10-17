"""Behavioral tests for the Everything SDK wrapper (everything_sdk.py).

The real Everything64.dll only exists on Windows, so tests inject a fake DLL
object through EverythingSDK's loader and drive the wrapper through its public
API on any platform.
"""

import ctypes
import datetime
import logging
import sys
from typing import Any, Callable, Dict, List, Optional

import pytest

from mcp_server_everything_search import everything_sdk as sdk_module
from mcp_server_everything_search.everything_sdk import (
    EPOCH_DIFF,
    EVERYTHING_ERROR_CREATETHREAD,
    EVERYTHING_ERROR_CREATEWINDOW,
    EVERYTHING_ERROR_INVALIDCALL,
    EVERYTHING_ERROR_INVALIDINDEX,
    EVERYTHING_ERROR_IPC,
    EVERYTHING_ERROR_MEMORY,
    EVERYTHING_ERROR_REGISTERCLASSEX,
    EVERYTHING_OK,
    EVERYTHING_REQUEST_ATTRIBUTES,
    EVERYTHING_REQUEST_DATE_ACCESSED,
    EVERYTHING_REQUEST_DATE_CREATED,
    EVERYTHING_REQUEST_DATE_MODIFIED,
    EVERYTHING_REQUEST_DATE_RECENTLY_CHANGED,
    EVERYTHING_REQUEST_DATE_RUN,
    EVERYTHING_REQUEST_EXTENSION,
    EVERYTHING_REQUEST_FILE_LIST_FILE_NAME,
    EVERYTHING_REQUEST_FILE_NAME,
    EVERYTHING_REQUEST_FULL_PATH_AND_FILE_NAME,
    EVERYTHING_REQUEST_HIGHLIGHTED_FILE_NAME,
    EVERYTHING_REQUEST_HIGHLIGHTED_FULL_PATH_AND_FILE_NAME,
    EVERYTHING_REQUEST_HIGHLIGHTED_PATH,
    EVERYTHING_REQUEST_PATH,
    EVERYTHING_REQUEST_RUN_COUNT,
    EVERYTHING_REQUEST_SIZE,
    EVERYTHING_SORT_ATTRIBUTES_ASCENDING,
    EVERYTHING_SORT_ATTRIBUTES_DESCENDING,
    EVERYTHING_SORT_DATE_ACCESSED_ASCENDING,
    EVERYTHING_SORT_DATE_ACCESSED_DESCENDING,
    EVERYTHING_SORT_DATE_CREATED_ASCENDING,
    EVERYTHING_SORT_DATE_CREATED_DESCENDING,
    EVERYTHING_SORT_DATE_MODIFIED_ASCENDING,
    EVERYTHING_SORT_DATE_MODIFIED_DESCENDING,
    EVERYTHING_SORT_DATE_RECENTLY_CHANGED_ASCENDING,
    EVERYTHING_SORT_DATE_RECENTLY_CHANGED_DESCENDING,
    EVERYTHING_SORT_DATE_RUN_ASCENDING,
    EVERYTHING_SORT_DATE_RUN_DESCENDING,
    EVERYTHING_SORT_EXTENSION_ASCENDING,
    EVERYTHING_SORT_EXTENSION_DESCENDING,
    EVERYTHING_SORT_FILE_LIST_FILENAME_ASCENDING,
    EVERYTHING_SORT_FILE_LIST_FILENAME_DESCENDING,
    EVERYTHING_SORT_NAME_ASCENDING,
    EVERYTHING_SORT_NAME_DESCENDING,
    EVERYTHING_SORT_PATH_ASCENDING,
    EVERYTHING_SORT_PATH_DESCENDING,
    EVERYTHING_SORT_RUN_COUNT_ASCENDING,
    EVERYTHING_SORT_RUN_COUNT_DESCENDING,
    EVERYTHING_SORT_SIZE_ASCENDING,
    EVERYTHING_SORT_SIZE_DESCENDING,
    EVERYTHING_SORT_TYPE_NAME_ASCENDING,
    EVERYTHING_SORT_TYPE_NAME_DESCENDING,
    POSIX_EPOCH,
    WINDOWS_EPOCH,
    WINDOWS_TICKS,
    WINDOWS_TICKS_TO_POSIX_EPOCH,
    EverythingError,
    EverythingSDK,
    SearchResult,
)

UNREPRESENTABLE_FILETIME = 2**64 - 1


def _filetime(value: datetime.datetime) -> int:
    return int(value.timestamp() * WINDOWS_TICKS + WINDOWS_TICKS_TO_POSIX_EPOCH)


class _Fn:
    """A fake DLL function: callable, records calls, accepts argtypes/restype."""

    argtypes: Any = None
    restype: Any = None

    def __init__(self, impl: Callable[..., Any]):
        self.impl = impl
        self.calls: List[tuple] = []

    def __call__(self, *args: Any) -> Any:
        self.calls.append(args)
        return self.impl(*args)


class FakeEverythingDLL:
    """In-memory stand-in for Everything64.dll."""

    def __init__(
        self,
        results: Optional[List[Dict[str, Any]]] = None,
        query_ok: bool = True,
        last_error: int = EVERYTHING_OK,
        unreadable: tuple = (),
    ):
        self.results = results or []
        self.unreadable = unreadable

        def row(i: int) -> Dict[str, Any]:
            return self.results[i]

        def filename(i: int) -> str:
            if i in self.unreadable:
                raise OSError(f"cannot read result {i}")
            return row(i)["filename"]

        def full_path(i: int, buffer: Any, size: int) -> None:
            buffer.value = row(i)["path"]

        def setter(key: str) -> Callable[[int, Any], None]:
            def _set(i: int, target: Any) -> None:
                target.value = row(i).get(key, 0)

            return _set

        noop = _Fn(lambda *a: None)
        self.Everything_SetSearchW = _Fn(lambda q: None)
        self.Everything_SetMatchPath = _Fn(lambda v: None)
        self.Everything_SetMatchCase = _Fn(lambda v: None)
        self.Everything_SetMatchWholeWord = _Fn(lambda v: None)
        self.Everything_SetRegex = _Fn(lambda v: None)
        self.Everything_SetMax = _Fn(lambda v: None)
        self.Everything_SetSort = _Fn(lambda v: None)
        self.Everything_SetRequestFlags = _Fn(lambda v: None)
        self.Everything_QueryW = _Fn(lambda wait: query_ok)
        self.Everything_GetNumResults = _Fn(lambda: len(self.results))
        self.Everything_GetLastError = _Fn(lambda: last_error)
        self.Everything_GetResultFileNameW = _Fn(filename)
        self.Everything_GetResultExtensionW = _Fn(lambda i: row(i).get("extension"))
        self.Everything_GetResultPathW = _Fn(lambda i: row(i)["path"])
        self.Everything_GetResultFullPathNameW = _Fn(full_path)
        self.Everything_GetResultDateCreated = _Fn(setter("created"))
        self.Everything_GetResultDateModified = _Fn(setter("modified"))
        self.Everything_GetResultDateAccessed = _Fn(setter("accessed"))
        self.Everything_GetResultSize = _Fn(setter("size"))
        self.Everything_GetResultAttributes = _Fn(
            lambda i: row(i).get("attributes", 32)
        )
        self.Everything_GetResultRunCount = _Fn(lambda i: row(i).get("run_count", 0))
        self.Everything_GetResultHighlightedFileNameW = _Fn(
            lambda i: row(i)["filename"]
        )
        self.Everything_GetResultHighlightedPathW = _Fn(lambda i: row(i)["path"])
        self.Everything_Reset = noop


WHEN = datetime.datetime(2026, 1, 2, 3, 4, 5)
REPORT = {
    "path": r"C:\docs\report.pdf",
    "filename": "report.pdf",
    "extension": "pdf",
    "size": 1234,
    "created": _filetime(WHEN),
    "modified": _filetime(WHEN),
    "accessed": 0,
}


def _sdk(dll: FakeEverythingDLL) -> EverythingSDK:
    return EverythingSDK("Everything64.dll", loader=lambda path: dll)


# --- module constants and models ---


def test_sdk_constants_match_everything_sdk_header():
    assert {
        "OK": EVERYTHING_OK,
        "ERROR_MEMORY": EVERYTHING_ERROR_MEMORY,
        "ERROR_IPC": EVERYTHING_ERROR_IPC,
        "ERROR_REGISTERCLASSEX": EVERYTHING_ERROR_REGISTERCLASSEX,
        "ERROR_CREATEWINDOW": EVERYTHING_ERROR_CREATEWINDOW,
        "ERROR_CREATETHREAD": EVERYTHING_ERROR_CREATETHREAD,
        "ERROR_INVALIDINDEX": EVERYTHING_ERROR_INVALIDINDEX,
        "ERROR_INVALIDCALL": EVERYTHING_ERROR_INVALIDCALL,
        "REQUEST_FILE_NAME": EVERYTHING_REQUEST_FILE_NAME,
        "REQUEST_PATH": EVERYTHING_REQUEST_PATH,
        "REQUEST_FULL_PATH_AND_FILE_NAME": EVERYTHING_REQUEST_FULL_PATH_AND_FILE_NAME,
        "REQUEST_EXTENSION": EVERYTHING_REQUEST_EXTENSION,
        "REQUEST_SIZE": EVERYTHING_REQUEST_SIZE,
        "REQUEST_DATE_CREATED": EVERYTHING_REQUEST_DATE_CREATED,
        "REQUEST_DATE_MODIFIED": EVERYTHING_REQUEST_DATE_MODIFIED,
        "REQUEST_DATE_ACCESSED": EVERYTHING_REQUEST_DATE_ACCESSED,
        "REQUEST_ATTRIBUTES": EVERYTHING_REQUEST_ATTRIBUTES,
        "REQUEST_FILE_LIST_FILE_NAME": EVERYTHING_REQUEST_FILE_LIST_FILE_NAME,
        "REQUEST_RUN_COUNT": EVERYTHING_REQUEST_RUN_COUNT,
        "REQUEST_DATE_RUN": EVERYTHING_REQUEST_DATE_RUN,
        "REQUEST_DATE_RECENTLY_CHANGED": EVERYTHING_REQUEST_DATE_RECENTLY_CHANGED,
        "REQUEST_HIGHLIGHTED_FILE_NAME": EVERYTHING_REQUEST_HIGHLIGHTED_FILE_NAME,
        "REQUEST_HIGHLIGHTED_PATH": EVERYTHING_REQUEST_HIGHLIGHTED_PATH,
        "REQUEST_HIGHLIGHTED_FULL_PATH_AND_FILE_NAME": EVERYTHING_REQUEST_HIGHLIGHTED_FULL_PATH_AND_FILE_NAME,
        "SORT_NAME_ASCENDING": EVERYTHING_SORT_NAME_ASCENDING,
        "SORT_NAME_DESCENDING": EVERYTHING_SORT_NAME_DESCENDING,
        "SORT_PATH_ASCENDING": EVERYTHING_SORT_PATH_ASCENDING,
        "SORT_PATH_DESCENDING": EVERYTHING_SORT_PATH_DESCENDING,
        "SORT_SIZE_ASCENDING": EVERYTHING_SORT_SIZE_ASCENDING,
        "SORT_SIZE_DESCENDING": EVERYTHING_SORT_SIZE_DESCENDING,
        "SORT_EXTENSION_ASCENDING": EVERYTHING_SORT_EXTENSION_ASCENDING,
        "SORT_EXTENSION_DESCENDING": EVERYTHING_SORT_EXTENSION_DESCENDING,
        "SORT_TYPE_NAME_ASCENDING": EVERYTHING_SORT_TYPE_NAME_ASCENDING,
        "SORT_TYPE_NAME_DESCENDING": EVERYTHING_SORT_TYPE_NAME_DESCENDING,
        "SORT_DATE_CREATED_ASCENDING": EVERYTHING_SORT_DATE_CREATED_ASCENDING,
        "SORT_DATE_CREATED_DESCENDING": EVERYTHING_SORT_DATE_CREATED_DESCENDING,
        "SORT_DATE_MODIFIED_ASCENDING": EVERYTHING_SORT_DATE_MODIFIED_ASCENDING,
        "SORT_DATE_MODIFIED_DESCENDING": EVERYTHING_SORT_DATE_MODIFIED_DESCENDING,
        "SORT_ATTRIBUTES_ASCENDING": EVERYTHING_SORT_ATTRIBUTES_ASCENDING,
        "SORT_ATTRIBUTES_DESCENDING": EVERYTHING_SORT_ATTRIBUTES_DESCENDING,
        "SORT_FILE_LIST_FILENAME_ASCENDING": EVERYTHING_SORT_FILE_LIST_FILENAME_ASCENDING,
        "SORT_FILE_LIST_FILENAME_DESCENDING": EVERYTHING_SORT_FILE_LIST_FILENAME_DESCENDING,
        "SORT_RUN_COUNT_ASCENDING": EVERYTHING_SORT_RUN_COUNT_ASCENDING,
        "SORT_RUN_COUNT_DESCENDING": EVERYTHING_SORT_RUN_COUNT_DESCENDING,
        "SORT_DATE_RECENTLY_CHANGED_ASCENDING": EVERYTHING_SORT_DATE_RECENTLY_CHANGED_ASCENDING,
        "SORT_DATE_RECENTLY_CHANGED_DESCENDING": EVERYTHING_SORT_DATE_RECENTLY_CHANGED_DESCENDING,
        "SORT_DATE_ACCESSED_ASCENDING": EVERYTHING_SORT_DATE_ACCESSED_ASCENDING,
        "SORT_DATE_ACCESSED_DESCENDING": EVERYTHING_SORT_DATE_ACCESSED_DESCENDING,
        "SORT_DATE_RUN_ASCENDING": EVERYTHING_SORT_DATE_RUN_ASCENDING,
        "SORT_DATE_RUN_DESCENDING": EVERYTHING_SORT_DATE_RUN_DESCENDING,
    } == {
        "OK": 0,
        "ERROR_MEMORY": 1,
        "ERROR_IPC": 2,
        "ERROR_REGISTERCLASSEX": 3,
        "ERROR_CREATEWINDOW": 4,
        "ERROR_CREATETHREAD": 5,
        "ERROR_INVALIDINDEX": 6,
        "ERROR_INVALIDCALL": 7,
        "REQUEST_FILE_NAME": 0x1,
        "REQUEST_PATH": 0x2,
        "REQUEST_FULL_PATH_AND_FILE_NAME": 0x4,
        "REQUEST_EXTENSION": 0x8,
        "REQUEST_SIZE": 0x10,
        "REQUEST_DATE_CREATED": 0x20,
        "REQUEST_DATE_MODIFIED": 0x40,
        "REQUEST_DATE_ACCESSED": 0x80,
        "REQUEST_ATTRIBUTES": 0x100,
        "REQUEST_FILE_LIST_FILE_NAME": 0x200,
        "REQUEST_RUN_COUNT": 0x400,
        "REQUEST_DATE_RUN": 0x800,
        "REQUEST_DATE_RECENTLY_CHANGED": 0x1000,
        "REQUEST_HIGHLIGHTED_FILE_NAME": 0x2000,
        "REQUEST_HIGHLIGHTED_PATH": 0x4000,
        "REQUEST_HIGHLIGHTED_FULL_PATH_AND_FILE_NAME": 0x8000,
        "SORT_NAME_ASCENDING": 1,
        "SORT_NAME_DESCENDING": 2,
        "SORT_PATH_ASCENDING": 3,
        "SORT_PATH_DESCENDING": 4,
        "SORT_SIZE_ASCENDING": 5,
        "SORT_SIZE_DESCENDING": 6,
        "SORT_EXTENSION_ASCENDING": 7,
        "SORT_EXTENSION_DESCENDING": 8,
        "SORT_TYPE_NAME_ASCENDING": 9,
        "SORT_TYPE_NAME_DESCENDING": 10,
        "SORT_DATE_CREATED_ASCENDING": 11,
        "SORT_DATE_CREATED_DESCENDING": 12,
        "SORT_DATE_MODIFIED_ASCENDING": 13,
        "SORT_DATE_MODIFIED_DESCENDING": 14,
        "SORT_ATTRIBUTES_ASCENDING": 15,
        "SORT_ATTRIBUTES_DESCENDING": 16,
        "SORT_FILE_LIST_FILENAME_ASCENDING": 17,
        "SORT_FILE_LIST_FILENAME_DESCENDING": 18,
        "SORT_RUN_COUNT_ASCENDING": 19,
        "SORT_RUN_COUNT_DESCENDING": 20,
        "SORT_DATE_RECENTLY_CHANGED_ASCENDING": 21,
        "SORT_DATE_RECENTLY_CHANGED_DESCENDING": 22,
        "SORT_DATE_ACCESSED_ASCENDING": 23,
        "SORT_DATE_ACCESSED_DESCENDING": 24,
        "SORT_DATE_RUN_ASCENDING": 25,
        "SORT_DATE_RUN_DESCENDING": 26,
    }


def test_windows_filetime_constants_describe_the_1601_epoch():
    assert WINDOWS_TICKS == 10_000_000
    assert (WINDOWS_EPOCH, POSIX_EPOCH) == (
        datetime.datetime(1601, 1, 1),
        datetime.datetime(1970, 1, 1),
    )
    assert EPOCH_DIFF == 11_644_473_600.0
    assert WINDOWS_TICKS_TO_POSIX_EPOCH == EPOCH_DIFF * WINDOWS_TICKS


def test_search_result_optional_fields_default_to_none():
    result = SearchResult(path=r"C:\a.txt", filename="a.txt", size=1)

    assert (result.extension, result.created, result.modified, result.accessed) == (
        None,
        None,
        None,
        None,
    )
    assert (result.attributes, result.run_count) == (None, None)
    assert (result.highlighted_filename, result.highlighted_path) == (None, None)


@pytest.mark.parametrize(
    ("code", "message"),
    [
        (EVERYTHING_ERROR_IPC, "IPC failed (Everything service not running?)"),
        (99, "Unknown error: 99"),
    ],
)
def test_everything_error_carries_code_and_message(code, message):
    error = EverythingError(code)

    assert error.error_code == code
    assert str(error) == message


# --- loading the DLL ---


def test_dll_load_failure_names_everything_sdk_path():
    def failing_loader(path: str) -> Any:
        raise OSError("module not found")

    with pytest.raises(RuntimeError, match="EVERYTHING_SDK_PATH"):
        EverythingSDK(r"C:\missing\Everything64.dll", loader=failing_loader)


def test_dll_without_everything_functions_is_rejected():
    with pytest.raises(RuntimeError, match="does not expose"):
        EverythingSDK("not-everything.dll", loader=lambda path: object())


@pytest.mark.skipif(
    sys.platform == "win32", reason="checks the non-Windows default loader"
)
def test_default_loader_off_windows_reports_windows_only():
    with pytest.raises(RuntimeError, match="only available on Windows"):
        EverythingSDK("Everything64.dll")


@pytest.mark.skipif(
    sys.platform != "win32", reason="exercises the real ctypes.WinDLL loader"
)
def test_default_loader_on_windows_reports_missing_dll_with_sdk_path_hint():
    with pytest.raises(RuntimeError, match="EVERYTHING_SDK_PATH"):
        EverythingSDK(r"C:\nonexistent\Everything64.dll")


def test_loaded_dll_is_exposed_and_configured():
    dll = FakeEverythingDLL()

    sdk = _sdk(dll)

    assert sdk.dll is dll
    assert dll.Everything_QueryW.restype is ctypes.c_bool


# --- searching ---


def test_search_configures_everything_and_returns_results():
    # Arrange
    dll = FakeEverythingDLL([{**REPORT, "attributes": 33, "run_count": 4}])

    # Act
    results = _sdk(dll).search_files(
        "report",
        max_results=5,
        match_path=True,
        match_case=True,
        match_whole_word=True,
        match_regex=True,
        sort_by=6,
    )

    # Assert
    assert dll.Everything_SetSearchW.calls == [("report",)]
    assert dll.Everything_SetMatchPath.calls == [(True,)]
    assert dll.Everything_SetMatchCase.calls == [(True,)]
    assert dll.Everything_SetMatchWholeWord.calls == [(True,)]
    assert dll.Everything_SetRegex.calls == [(True,)]
    assert dll.Everything_SetMax.calls == [(5,)]
    assert dll.Everything_SetSort.calls == [(6,)]
    [result] = results
    expected_time = datetime.datetime.fromtimestamp(
        (REPORT["created"] - WINDOWS_TICKS_TO_POSIX_EPOCH) / WINDOWS_TICKS
    ).isoformat()
    assert result.model_dump() == {
        "path": r"C:\docs\report.pdf",
        "filename": "report.pdf",
        "extension": "pdf",
        "size": 1234,
        "created": expected_time,
        "modified": expected_time,
        "accessed": None,
        "attributes": 33,
        "run_count": 4,
        "highlighted_filename": "report.pdf",
        "highlighted_path": r"C:\docs\report.pdf",
    }


def test_search_requests_the_default_result_fields():
    dll = FakeEverythingDLL([REPORT])

    _sdk(dll).search_files("report")

    assert dll.Everything_SetRequestFlags.calls == [
        (
            EVERYTHING_REQUEST_FILE_NAME
            | EVERYTHING_REQUEST_PATH
            | EVERYTHING_REQUEST_EXTENSION
            | EVERYTHING_REQUEST_SIZE
            | EVERYTHING_REQUEST_DATE_CREATED
            | EVERYTHING_REQUEST_DATE_MODIFIED
            | EVERYTHING_REQUEST_DATE_ACCESSED
            | EVERYTHING_REQUEST_ATTRIBUTES
            | EVERYTHING_REQUEST_RUN_COUNT
            | EVERYTHING_REQUEST_HIGHLIGHTED_FILE_NAME
            | EVERYTHING_REQUEST_HIGHLIGHTED_PATH,
        )
    ]


def test_search_with_no_matches_returns_empty_list():
    from mcp_server_everything_search.search_interface import PartialResults

    dll = FakeEverythingDLL([])

    results = _sdk(dll).search_files("nothing")

    assert results == []
    assert not isinstance(results, PartialResults)
    assert len(dll.Everything_Reset.calls) == 1


def test_search_returns_at_most_max_results():
    dll = FakeEverythingDLL([REPORT, REPORT, REPORT])

    assert len(_sdk(dll).search_files("report", max_results=2)) == 2


def test_unrepresentable_timestamp_becomes_none_and_keeps_result(caplog):
    # Arrange: one bad timestamp used to drop the whole result (#14)
    dll = FakeEverythingDLL([{**REPORT, "modified": UNREPRESENTABLE_FILETIME}])

    # Act
    with caplog.at_level(logging.WARNING):
        [result] = _sdk(dll).search_files("report")

    # Assert
    assert result.modified is None
    assert result.created is not None
    assert "modified" in caplog.text


def test_unreadable_results_are_returned_as_partial_results(caplog):
    # Arrange
    from mcp_server_everything_search.search_interface import PartialResults

    dll = FakeEverythingDLL(
        [REPORT, {**REPORT, "filename": "b.txt"}, REPORT], unreadable=(1,)
    )

    # Act
    with caplog.at_level(logging.WARNING):
        results = _sdk(dll).search_files("x")

    # Assert
    assert isinstance(results, PartialResults)
    assert (len(results), results.unreadable) == (2, 1)
    assert "cannot read result 1" in caplog.text


def test_complete_results_are_not_marked_partial():
    from mcp_server_everything_search.search_interface import PartialResults

    results = _sdk(FakeEverythingDLL([REPORT])).search_files("x")

    assert not isinstance(results, PartialResults)


def test_all_results_unreadable_raises():
    dll = FakeEverythingDLL([REPORT, REPORT], unreadable=(0, 1))

    with pytest.raises(RuntimeError, match="all 2"):
        _sdk(dll).search_files("x")

    assert len(dll.Everything_Reset.calls) == 1


def test_everything_is_reset_after_a_successful_search():
    dll = FakeEverythingDLL([REPORT])

    _sdk(dll).search_files("x")

    assert len(dll.Everything_Reset.calls) == 1


def test_result_with_null_filename_counts_as_unreadable():
    # A real DLL returns NULL for an unreadable name; the model then rejects it
    from mcp_server_everything_search.search_interface import PartialResults

    dll = FakeEverythingDLL([REPORT, {**REPORT, "filename": None}])

    results = _sdk(dll).search_files("x")

    assert isinstance(results, PartialResults)
    assert (len(results), results.unreadable) == (1, 1)


def test_query_failure_raises_everything_error():
    dll = FakeEverythingDLL(query_ok=False, last_error=EVERYTHING_ERROR_IPC)

    with pytest.raises(EverythingError, match="IPC failed"):
        _sdk(dll).search_files("x")


def test_query_failure_without_error_code_raises_runtime_error():
    dll = FakeEverythingDLL(query_ok=False, last_error=EVERYTHING_OK)

    with pytest.raises(RuntimeError, match="without reporting an error code"):
        _sdk(dll).search_files("x")


def test_everything_is_reset_even_when_the_query_fails():
    dll = FakeEverythingDLL(query_ok=False, last_error=EVERYTHING_ERROR_IPC)

    with pytest.raises(EverythingError):
        _sdk(dll).search_files("x")

    assert len(dll.Everything_Reset.calls) == 1


def test_search_does_not_print_debug_output(capsys):
    _sdk(FakeEverythingDLL([REPORT])).search_files("x")

    # stdout carries the MCP protocol; stray output would corrupt it
    assert capsys.readouterr() == ("", "")


def test_module_uses_logging_for_diagnostics():
    assert isinstance(sdk_module.logger, logging.Logger)


# --- partial results in tool output ---


def test_partial_results_behave_like_a_list_with_an_unreadable_count():
    from mcp_server_everything_search.search_interface import PartialResults

    results = PartialResults(["a", "b"], unreadable=3)

    assert (list(results), len(results), results.unreadable) == (["a", "b"], 2, 3)


def test_format_results_warns_when_results_are_partial():
    # Arrange
    from mcp_server_everything_search.search_interface import (
        PartialResults,
        SearchResult as Result,
    )
    from mcp_server_everything_search.server import format_results

    results = PartialResults([Result(path="/a", filename="a", size=1)], unreadable=2)

    # Act
    text = format_results(results)

    # Assert
    assert text.startswith("Path: /a\n")
    assert text.endswith(
        "Warning: 2 matching result(s) could not be read and were omitted. See the server log."
    )


def test_windows_provider_surfaces_unreadable_results_in_tool_output():
    # Arrange: SDK -> WindowsSearchProvider -> format_results, all public
    from mcp_server_everything_search.search_interface import WindowsSearchProvider
    from mcp_server_everything_search.server import format_results

    sdk = _sdk(FakeEverythingDLL([REPORT, REPORT], unreadable=(1,)))
    provider = WindowsSearchProvider(everything_sdk=sdk)

    # Act
    text = format_results(provider.search_files("report"))

    # Assert
    assert text.count("Path: ") == 1
    assert text.endswith(
        "Warning: 1 matching result(s) could not be read and were omitted. See the server log."
    )
