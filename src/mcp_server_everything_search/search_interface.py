"""Platform-agnostic search interface for MCP."""

import abc
import platform
import subprocess
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass

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
            if match_name := not match_path:
                cmd.extend(['-name', query])
            else:
                cmd.append(query)
            
            # Execute search
            result = subprocess.run(cmd, capture_output=True, text=True)
            paths = result.stdout.splitlines()[:max_results]
            
            # Convert to SearchResult objects
            results = []
            for path in paths:
                import os
                filename = os.path.basename(path)
                _, ext = os.path.splitext(filename)
                stat = os.stat(path)
                
                results.append(SearchResult(
                    path=path,
                    filename=filename,
                    extension=ext[1:] if ext else None,
                    size=stat.st_size,
                    created=datetime.fromtimestamp(stat.st_ctime),
                    modified=datetime.fromtimestamp(stat.st_mtime),
                    accessed=datetime.fromtimestamp(stat.st_atime)
                ))
            
            return results
            
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Search failed: {e}")

class LinuxSearchProvider(SearchProvider):
    """Linux search implementation using locate."""
    
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
            cmd = ['locate']
            if not match_case:
                cmd.append('-i')
            if match_regex:
                cmd.append('--regex')
            cmd.append(query)
            
            # Execute search
            result = subprocess.run(cmd, capture_output=True, text=True)
            paths = result.stdout.splitlines()[:max_results]
            
            # Convert to SearchResult objects
            results = []
            for path in paths:
                import os
                filename = os.path.basename(path)
                _, ext = os.path.splitext(filename)
                try:
                    stat = os.stat(path)
                    results.append(SearchResult(
                        path=path,
                        filename=filename,
                        extension=ext[1:] if ext else None,
                        size=stat.st_size,
                        created=datetime.fromtimestamp(stat.st_ctime),
                        modified=datetime.fromtimestamp(stat.st_mtime),
                        accessed=datetime.fromtimestamp(stat.st_atime)
                    ))
                except OSError:
                    # Skip files we can't access
                    continue
            
            return results
            
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
