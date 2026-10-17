"""Platform-agnostic search interface for MCP."""

import abc
import os
import platform
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable, List, Optional, Protocol, runtime_checkable


@dataclass
class SearchResult:
    """Universal search result structure."""

    path: str
    filename: str
    extension: Optional[str] = None
    size: Optional[int] = None
    created: Optional[datetime] = None
    modified: Optional[datetime] = None
    accessed: Optional[datetime] = None
    attributes: Optional[str] = None


class PartialResults(List[Any]):
    """Search results where some matches could not be read; `unreadable` counts them."""

    def __init__(self, results: Iterable[Any] = (), unreadable: int = 0) -> None:
        super().__init__(results)
        self.unreadable = unreadable


def run_command(cmd: List[str]) -> "subprocess.CompletedProcess[str]":
    """Run a command and capture its text output (default command runner)."""
    return subprocess.run(cmd, capture_output=True, text=True)


_LOCATE_INSTALL_HINT = (
    "Ubuntu/Debian: sudo apt-get install plocate\n"
    "              or\n"
    "              sudo apt-get install mlocate\n"
    "Fedora: sudo dnf install mlocate"
)

# Everything SDK EVERYTHING_SORT_NAME_ASCENDING
_EVERYTHING_DEFAULT_SORT = 1


class SearchProvider(abc.ABC):
    """Abstract base class for platform-specific search implementations."""

    @abc.abstractmethod
    def search_files(self, query: str, max_results: int = 100) -> List[SearchResult]:
        """Execute a file search using platform-specific methods."""

    def count_files(
        self,
        query: str,
        ignore_case: bool = True,
        regex_search: bool = False,
        existing_files: bool = True,
    ) -> int:
        """Count matches without listing them. Only supported on Linux."""
        raise NotImplementedError("count_only is only supported on Linux (locate -c)")

    @classmethod
    def get_provider(cls) -> "SearchProvider":
        """Factory method to get the appropriate search provider for the current platform."""
        system = platform.system().lower()
        if system == "darwin":
            return MacSearchProvider()
        elif system == "linux":
            return LinuxSearchProvider()
        elif system == "windows":
            return WindowsSearchProvider()
        else:
            raise NotImplementedError(f"No search provider available for {system}")

    def _convert_path_to_result(self, path: str) -> SearchResult:
        """Convert a path to a SearchResult with file information."""
        try:
            path_obj = Path(path)
            stat = path_obj.stat()
            return SearchResult(
                path=str(path_obj),
                filename=path_obj.name,
                extension=path_obj.suffix[1:] if path_obj.suffix else None,
                size=stat.st_size,
                created=datetime.fromtimestamp(stat.st_ctime),
                modified=datetime.fromtimestamp(stat.st_mtime),
                accessed=datetime.fromtimestamp(stat.st_atime),
            )
        except (OSError, ValueError):
            # If we can't access the file, return basic info
            return SearchResult(path=str(path), filename=os.path.basename(path))


class MacSearchProvider(SearchProvider):
    """macOS search implementation using mdfind."""

    def __init__(
        self,
        run_command: Callable[
            [List[str]], "subprocess.CompletedProcess[str]"
        ] = run_command,
    ) -> None:
        self._run = run_command

    def search_files(
        self,
        query: str,
        max_results: int = 100,
        search_directory: Optional[str] = None,
        live_updates: bool = False,
        literal_query: bool = False,
        interpret_query: bool = False,
    ) -> List[SearchResult]:
        if live_updates:
            raise ValueError(
                "live_updates is not supported: mdfind -live never exits, so the search would not return"
            )

        cmd = ["mdfind"]
        if search_directory:
            cmd.extend(["-onlyin", search_directory])
        if literal_query:
            cmd.append("-literal")
        if interpret_query:
            cmd.append("-interpret")
        if literal_query or interpret_query:
            # -literal / -interpret apply to a raw Spotlight query
            cmd.append(query)
        else:
            cmd.extend(["-name", query])

        result = self._run(cmd)
        if result.returncode != 0:
            raise RuntimeError(f"mdfind failed: {result.stderr}")

        paths = result.stdout.splitlines()[:max_results]
        return [self._convert_path_to_result(path) for path in paths]


class LinuxSearchProvider(SearchProvider):
    """Linux search implementation using locate/plocate."""

    def __init__(
        self,
        run_command: Callable[
            [List[str]], "subprocess.CompletedProcess[str]"
        ] = run_command,
    ) -> None:
        """Check if locate/plocate is installed."""
        self._run = run_command

        # Check for plocate first (newer version)
        if self._run(["which", "plocate"]).returncode == 0:
            self.locate_cmd = "plocate"
            self.locate_type = "plocate"
        elif self._run(["which", "locate"]).returncode == 0:
            self.locate_cmd = "locate"
            self.locate_type = "mlocate"
        else:
            raise RuntimeError(
                "Neither 'locate' nor 'plocate' is installed. Please install one:\n"
                + _LOCATE_INSTALL_HINT
                + "\nAfter installation, the database will be updated automatically, or run:\n"
                "For plocate: sudo updatedb\n"
                "For mlocate: sudo /etc/cron.daily/mlocate"
            )

    def _base_command(
        self, ignore_case: bool, regex_search: bool, existing_files: bool
    ) -> List[str]:
        cmd = [self.locate_cmd]
        if ignore_case:
            cmd.append("-i")
        if regex_search:
            cmd.append("--regex" if self.locate_type == "mlocate" else "-r")
        if existing_files:
            cmd.append("-e")
        return cmd

    def _execute(self, cmd: List[str]) -> str:
        try:
            result = self._run(cmd)
        except FileNotFoundError:
            raise RuntimeError(
                f"The {self.locate_cmd} command disappeared. Please reinstall:\n"
                + _LOCATE_INSTALL_HINT
            )
        if result.returncode != 0:
            error_msg = result.stderr.lower()
            if "no such file or directory" in error_msg or "database" in error_msg:
                raise RuntimeError(
                    f"The {self.locate_type} database needs to be created. Please run: sudo updatedb"
                )
            raise RuntimeError(f"{self.locate_cmd} failed: {result.stderr}")
        return result.stdout

    def search_files(
        self,
        query: str,
        max_results: int = 100,
        ignore_case: bool = True,
        regex_search: bool = False,
        existing_files: bool = True,
    ) -> List[SearchResult]:
        cmd = self._base_command(ignore_case, regex_search, existing_files)
        cmd.extend(["-l", str(max_results), query])
        paths = self._execute(cmd).splitlines()[:max_results]
        return [self._convert_path_to_result(path) for path in paths]

    def count_files(
        self,
        query: str,
        ignore_case: bool = True,
        regex_search: bool = False,
        existing_files: bool = True,
    ) -> int:
        cmd = self._base_command(ignore_case, regex_search, existing_files)
        cmd.extend(["-c", query])
        output = self._execute(cmd).strip()
        try:
            return int(output)
        except ValueError:
            raise RuntimeError(
                f"Failed to parse match count from {self.locate_cmd} output: {output!r}"
            )


@runtime_checkable
class EverythingBackend(Protocol):
    """The part of the Everything SDK the Windows provider uses."""

    @abc.abstractmethod
    def search_files(
        self,
        *,
        query: str,
        max_results: int,
        match_path: bool,
        match_case: bool,
        match_whole_word: bool,
        match_regex: bool,
        sort_by: int,
    ) -> List[Any]: ...


class WindowsSearchProvider(SearchProvider):
    """Windows search implementation using Everything SDK."""

    def __init__(self, everything_sdk: Optional[EverythingBackend] = None) -> None:
        """Use the given backend, or load Everything64.dll from EVERYTHING_SDK_PATH."""
        if everything_sdk is None:
            from .everything_sdk import EverythingSDK

            dll_path = os.getenv(
                "EVERYTHING_SDK_PATH",
                "D:\\dev\\tools\\Everything-SDK\\dll\\Everything64.dll",
            )
            everything_sdk = EverythingSDK(dll_path)
        self.everything_sdk: EverythingBackend = everything_sdk

    def search_files(
        self,
        query: str,
        max_results: int = 100,
        match_path: bool = False,
        match_case: bool = False,
        match_whole_word: bool = False,
        match_regex: bool = False,
        sort_by: Optional[int] = None,
    ) -> List[SearchResult]:
        # Replace double backslashes with single backslashes
        query = query.replace("\\\\", "\\")
        # If the query contains forward slashes, replace them with backslashes
        query = query.replace("/", "\\")

        return self.everything_sdk.search_files(
            query=query,
            max_results=max_results,
            match_path=match_path,
            match_case=match_case,
            match_whole_word=match_whole_word,
            match_regex=match_regex,
            sort_by=_EVERYTHING_DEFAULT_SORT if sort_by is None else sort_by,
        )
