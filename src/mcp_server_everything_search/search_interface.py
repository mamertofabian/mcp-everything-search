"""Platform-agnostic search interface for MCP."""

import abc
import platform
import subprocess
import os
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass
from pathlib import Path

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

class SearchProvider(abc.ABC):
    """Abstract base class for platform-specific search implementations."""
    
    @abc.abstractmethod
    def search_files(
        self,
        query: str,
        max_results: int = 100,
        match_path: bool = False,
        match_case: bool = False,
        match_whole_word: bool = False,
        match_regex: bool = False,
        sort_by: Optional[int] = None
    ) -> List[SearchResult]:
        """Execute a file search using platform-specific methods."""
        pass

    @classmethod
    def get_provider(cls) -> 'SearchProvider':
        """Factory method to get the appropriate search provider for the current platform."""
        system = platform.system().lower()
        if system == 'darwin':
            return MacSearchProvider()
        elif system == 'linux':
            return LinuxSearchProvider()
        elif system == 'windows':
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
                accessed=datetime.fromtimestamp(stat.st_atime)
            )
        except (OSError, ValueError) as e:
            # If we can't access the file, return basic info
            return SearchResult(
                path=str(path),
                filename=os.path.basename(path)
            )

class MacSearchProvider(SearchProvider):
    """macOS search implementation using mdfind."""
    
    def search_files(
        self,
        query: str,
        max_results: int = 100,
        match_path: bool = False,
        match_case: bool = False,
        match_whole_word: bool = False,
        match_regex: bool = False,
        sort_by: Optional[int] = None
    ) -> List[SearchResult]:
        try:
            # Build mdfind command
            cmd = ['mdfind']
            if match_path:
                # When matching path, don't use -name
                cmd.append(query)
            else:
                cmd.extend(['-name', query])
            
            # Execute search
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(f"mdfind failed: {result.stderr}")

            # Process results
            paths = result.stdout.splitlines()[:max_results]
            return [self._convert_path_to_result(path) for path in paths]
            
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Search failed: {e}")

class LinuxSearchProvider(SearchProvider):
    """Linux search implementation using locate/plocate."""

    def __init__(self):
        """Check if locate/plocate is installed and the database is ready."""
        self.locate_cmd = None
        self.locate_type = None

        # Check for plocate first (newer version)
        plocate_check = subprocess.run(['which', 'plocate'], capture_output=True)
        if plocate_check.returncode == 0:
            self.locate_cmd = 'plocate'
            self.locate_type = 'plocate'
        else:
            # Check for mlocate
            mlocate_check = subprocess.run(['which', 'locate'], capture_output=True)
            if mlocate_check.returncode == 0:
                self.locate_cmd = 'locate'
                self.locate_type = 'mlocate'
            else:
                raise RuntimeError(
                    "Neither 'locate' nor 'plocate' is installed. Please install one:\n"
                    "Ubuntu/Debian: sudo apt-get install plocate\n"
                    "              or\n"
                    "              sudo apt-get install mlocate\n"
                    "Fedora: sudo dnf install mlocate\n"
                    "After installation, the database will be updated automatically, or run:\n"
                    "For plocate: sudo updatedb\n"
                    "For mlocate: sudo /etc/cron.daily/mlocate"
                )

    def _update_database(self):
        """Update the locate database."""
        if self.locate_type == 'plocate':
            subprocess.run(['sudo', 'updatedb'], check=True)
        else:  # mlocate
            subprocess.run(['sudo', '/etc/cron.daily/mlocate'], check=True)
    
    def search_files(
        self,
        query: str,
        max_results: int = 100,
        match_path: bool = False,
        match_case: bool = False,
        match_whole_word: bool = False,
        match_regex: bool = False,
        sort_by: Optional[int] = None
    ) -> List[SearchResult]:
        try:
            # Build locate command
            cmd = [self.locate_cmd]
            if not match_case:
                cmd.append('-i')
            if match_regex:
                cmd.append('--regex' if self.locate_type == 'mlocate' else '-r')
            cmd.append(query)
            
            # Execute search
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                error_msg = result.stderr.lower()
                if "no such file or directory" in error_msg or "database" in error_msg:
                    raise RuntimeError(
                        f"The {self.locate_type} database needs to be created. "
                        f"Please run: sudo updatedb"
                    )
                raise RuntimeError(f"{self.locate_cmd} failed: {result.stderr}")

            # Process results
            paths = result.stdout.splitlines()[:max_results]
            return [self._convert_path_to_result(path) for path in paths]
            
        except FileNotFoundError:
            raise RuntimeError(
                f"The {self.locate_cmd} command disappeared. Please reinstall:\n"
                "Ubuntu/Debian: sudo apt-get install plocate\n"
                "              or\n"
                "              sudo apt-get install mlocate\n"
                "Fedora: sudo dnf install mlocate"
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Search failed: {e}")


class WindowsSearchProvider(SearchProvider):
    """Windows search implementation using Everything SDK."""
    
    def __init__(self):
        """Initialize Everything SDK."""
        import os
        from .everything_sdk import EverythingSDK
        dll_path = os.getenv('EVERYTHING_SDK_PATH', 'D:\\dev\\tools\\Everything-SDK\\dll\\Everything64.dll')
        self.everything_sdk = EverythingSDK(dll_path)

    def search_files(
        self,
        query: str,
        max_results: int = 100,
        match_path: bool = False,
        match_case: bool = False,
        match_whole_word: bool = False,
        match_regex: bool = False,
        sort_by: Optional[int] = None
    ) -> List[SearchResult]:
        # Replace double backslashes with single backslashes
        query = query.replace("\\\\", "\\")
        # If the query.query contains forward slashes, replace them with backslashes
        query = query.replace("/", "\\")

        return self.everything_sdk.search_files(
            query=query,
            max_results=max_results,
            match_path=match_path,
            match_case=match_case,
            match_whole_word=match_whole_word,
            match_regex=match_regex,
            sort_by=sort_by
        )
    