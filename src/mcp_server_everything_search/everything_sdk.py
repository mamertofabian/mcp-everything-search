"""Everything SDK wrapper class."""

import ctypes
import datetime
import struct
import sys
from typing import Any, List
from pydantic import BaseModel

# Everything SDK constants
EVERYTHING_OK = 0
EVERYTHING_ERROR_MEMORY = 1
EVERYTHING_ERROR_IPC = 2
EVERYTHING_ERROR_REGISTERCLASSEX = 3
EVERYTHING_ERROR_CREATEWINDOW = 4
EVERYTHING_ERROR_CREATETHREAD = 5
EVERYTHING_ERROR_INVALIDINDEX = 6
EVERYTHING_ERROR_INVALIDCALL = 7

# Request flags
EVERYTHING_REQUEST_FILE_NAME = 0x00000001
EVERYTHING_REQUEST_PATH = 0x00000002
EVERYTHING_REQUEST_FULL_PATH_AND_FILE_NAME = 0x00000004
EVERYTHING_REQUEST_EXTENSION = 0x00000008
EVERYTHING_REQUEST_SIZE = 0x00000010
EVERYTHING_REQUEST_DATE_CREATED = 0x00000020
EVERYTHING_REQUEST_DATE_MODIFIED = 0x00000040
EVERYTHING_REQUEST_DATE_ACCESSED = 0x00000080
EVERYTHING_REQUEST_ATTRIBUTES = 0x00000100
EVERYTHING_REQUEST_FILE_LIST_FILE_NAME = 0x00000200
EVERYTHING_REQUEST_RUN_COUNT = 0x00000400
EVERYTHING_REQUEST_DATE_RUN = 0x00000800
EVERYTHING_REQUEST_DATE_RECENTLY_CHANGED = 0x00001000
EVERYTHING_REQUEST_HIGHLIGHTED_FILE_NAME = 0x00002000
EVERYTHING_REQUEST_HIGHLIGHTED_PATH = 0x00004000
EVERYTHING_REQUEST_HIGHLIGHTED_FULL_PATH_AND_FILE_NAME = 0x00008000

# Sort options
EVERYTHING_SORT_NAME_ASCENDING = 1
EVERYTHING_SORT_NAME_DESCENDING = 2
EVERYTHING_SORT_PATH_ASCENDING = 3
EVERYTHING_SORT_PATH_DESCENDING = 4
EVERYTHING_SORT_SIZE_ASCENDING = 5
EVERYTHING_SORT_SIZE_DESCENDING = 6
EVERYTHING_SORT_EXTENSION_ASCENDING = 7
EVERYTHING_SORT_EXTENSION_DESCENDING = 8
EVERYTHING_SORT_TYPE_NAME_ASCENDING = 9
EVERYTHING_SORT_TYPE_NAME_DESCENDING = 10
EVERYTHING_SORT_DATE_CREATED_ASCENDING = 11
EVERYTHING_SORT_DATE_CREATED_DESCENDING = 12
EVERYTHING_SORT_DATE_MODIFIED_ASCENDING = 13
EVERYTHING_SORT_DATE_MODIFIED_DESCENDING = 14
EVERYTHING_SORT_ATTRIBUTES_ASCENDING = 15
EVERYTHING_SORT_ATTRIBUTES_DESCENDING = 16
EVERYTHING_SORT_FILE_LIST_FILENAME_ASCENDING = 17
EVERYTHING_SORT_FILE_LIST_FILENAME_DESCENDING = 18
EVERYTHING_SORT_RUN_COUNT_ASCENDING = 19
EVERYTHING_SORT_RUN_COUNT_DESCENDING = 20
EVERYTHING_SORT_DATE_RECENTLY_CHANGED_ASCENDING = 21
EVERYTHING_SORT_DATE_RECENTLY_CHANGED_DESCENDING = 22
EVERYTHING_SORT_DATE_ACCESSED_ASCENDING = 23
EVERYTHING_SORT_DATE_ACCESSED_DESCENDING = 24
EVERYTHING_SORT_DATE_RUN_ASCENDING = 25
EVERYTHING_SORT_DATE_RUN_DESCENDING = 26

# Windows time conversion constants
WINDOWS_TICKS = int(1/10**-7)
WINDOWS_EPOCH = datetime.datetime.strptime('1601-01-01 00:00:00', '%Y-%m-%d %H:%M:%S')
POSIX_EPOCH = datetime.datetime.strptime('1970-01-01 00:00:00', '%Y-%m-%d %H:%M:%S')
EPOCH_DIFF = (POSIX_EPOCH - WINDOWS_EPOCH).total_seconds()
WINDOWS_TICKS_TO_POSIX_EPOCH = EPOCH_DIFF * WINDOWS_TICKS

class SearchResult(BaseModel):
    """Model for search results."""
    path: str
    filename: str
    extension: str | None = None
    size: int
    created: str | None = None
    modified: str | None = None
    accessed: str | None = None
    attributes: int | None = None
    run_count: int | None = None
    highlighted_filename: str | None = None
    highlighted_path: str | None = None

class EverythingError(Exception):
    """Custom exception for Everything SDK errors."""
    def __init__(self, error_code: int):
        self.error_code = error_code
        super().__init__(self._get_error_message())
    
    def _get_error_message(self) -> str:
        error_messages = {
            EVERYTHING_ERROR_MEMORY: "Failed to allocate memory",
            EVERYTHING_ERROR_IPC: "IPC failed (Everything service not running?)",
            EVERYTHING_ERROR_REGISTERCLASSEX: "Failed to register window class",
            EVERYTHING_ERROR_CREATEWINDOW: "Failed to create window",
            EVERYTHING_ERROR_CREATETHREAD: "Failed to create thread",
            EVERYTHING_ERROR_INVALIDINDEX: "Invalid index",
            EVERYTHING_ERROR_INVALIDCALL: "Invalid call"
        }
        return error_messages.get(self.error_code, f"Unknown error: {self.error_code}")

class EverythingSDK:
    """Wrapper for Everything SDK functionality."""
    
    def __init__(self, dll_path: str):
        """Initialize Everything SDK with the specified DLL path."""
        try:
            self.dll = ctypes.WinDLL(dll_path)
            self._configure_dll()
        except Exception as e:
            print(f"Failed to load Everything SDK DLL: {e}", file=sys.stderr)
            raise

    def _configure_dll(self):
        """Configure DLL function signatures."""
        # Search configuration
        self.dll.Everything_SetSearchW.argtypes = [ctypes.c_wchar_p]
        self.dll.Everything_SetMatchPath.argtypes = [ctypes.c_bool]
        self.dll.Everything_SetMatchCase.argtypes = [ctypes.c_bool]
        self.dll.Everything_SetMatchWholeWord.argtypes = [ctypes.c_bool]
        self.dll.Everything_SetRegex.argtypes = [ctypes.c_bool]
        self.dll.Everything_SetMax.argtypes = [ctypes.c_uint]
        self.dll.Everything_SetSort.argtypes = [ctypes.c_uint]
        self.dll.Everything_SetRequestFlags.argtypes = [ctypes.c_uint]

        # Query function
        self.dll.Everything_QueryW.argtypes = [ctypes.c_bool]
        self.dll.Everything_QueryW.restype = ctypes.c_bool

        # Result getters
        self.dll.Everything_GetNumResults.restype = ctypes.c_uint
        self.dll.Everything_GetLastError.restype = ctypes.c_uint
        
        self.dll.Everything_GetResultFileNameW.argtypes = [ctypes.c_uint]
        self.dll.Everything_GetResultFileNameW.restype = ctypes.c_wchar_p
        self.dll.Everything_GetResultExtensionW.argtypes = [ctypes.c_uint]
        self.dll.Everything_GetResultExtensionW.restype = ctypes.c_wchar_p
        self.dll.Everything_GetResultPathW.argtypes = [ctypes.c_uint]
        self.dll.Everything_GetResultPathW.restype = ctypes.c_wchar_p
        
        self.dll.Everything_GetResultFullPathNameW.argtypes = [
            ctypes.c_uint,
            ctypes.c_wchar_p,
            ctypes.c_uint
        ]
        
        self.dll.Everything_GetResultDateCreated.argtypes = [
            ctypes.c_uint, 
            ctypes.POINTER(ctypes.c_ulonglong)
        ]
        self.dll.Everything_GetResultDateModified.argtypes = [
            ctypes.c_uint, 
            ctypes.POINTER(ctypes.c_ulonglong)
        ]
        self.dll.Everything_GetResultDateAccessed.argtypes = [
            ctypes.c_uint, 
            ctypes.POINTER(ctypes.c_ulonglong)
        ]
        self.dll.Everything_GetResultSize.argtypes = [
            ctypes.c_uint, 
            ctypes.POINTER(ctypes.c_ulonglong)
        ]
        self.dll.Everything_GetResultAttributes.argtypes = [ctypes.c_uint]
        self.dll.Everything_GetResultRunCount.argtypes = [ctypes.c_uint]
        
        self.dll.Everything_GetResultHighlightedFileNameW.argtypes = [ctypes.c_uint]
        self.dll.Everything_GetResultHighlightedFileNameW.restype = ctypes.c_wchar_p
        self.dll.Everything_GetResultHighlightedPathW.argtypes = [ctypes.c_uint]
        self.dll.Everything_GetResultHighlightedPathW.restype = ctypes.c_wchar_p

    def _check_error(self):
        """Check for Everything SDK errors and raise appropriate exception."""
        error_code = self.dll.Everything_GetLastError()
        if error_code != EVERYTHING_OK:
            raise EverythingError(error_code)

    def _get_time(self, filetime: int) -> datetime.datetime:
        """Convert Windows filetime to Python datetime."""
        microsecs = (filetime - WINDOWS_TICKS_TO_POSIX_EPOCH) / WINDOWS_TICKS
        return datetime.datetime.fromtimestamp(microsecs)

    def search_files(
            self, 
            query: str, 
            max_results: int = 100,
            match_path: bool = False,
            match_case: bool = False,
            match_whole_word: bool = False,
            match_regex: bool = False,
            sort_by: int = EVERYTHING_SORT_NAME_ASCENDING,
            request_flags: int | None = None
        ) -> List[SearchResult]:
            """Perform file search using Everything SDK."""
            print(f"Debug: Setting up search with query: {query}", file=sys.stderr)
            
            # Set up search parameters
            self.dll.Everything_SetSearchW(query)
            self.dll.Everything_SetMatchPath(match_path)
            self.dll.Everything_SetMatchCase(match_case)
            self.dll.Everything_SetMatchWholeWord(match_whole_word)
            self.dll.Everything_SetRegex(match_regex)
            self.dll.Everything_SetMax(max_results)
            self.dll.Everything_SetSort(sort_by)

            # Set request flags
            if request_flags is None:
                request_flags = (
                    EVERYTHING_REQUEST_FILE_NAME |
                    EVERYTHING_REQUEST_PATH |
                    EVERYTHING_REQUEST_EXTENSION |
                    EVERYTHING_REQUEST_SIZE |
                    EVERYTHING_REQUEST_DATE_CREATED |
                    EVERYTHING_REQUEST_DATE_MODIFIED |
                    EVERYTHING_REQUEST_DATE_ACCESSED |
                    EVERYTHING_REQUEST_ATTRIBUTES |
                    EVERYTHING_REQUEST_RUN_COUNT |
                    EVERYTHING_REQUEST_HIGHLIGHTED_FILE_NAME |
                    EVERYTHING_REQUEST_HIGHLIGHTED_PATH
                )
            self.dll.Everything_SetRequestFlags(request_flags)

            # Execute search
            print("Debug: Executing search query", file=sys.stderr)
            if not self.dll.Everything_QueryW(True):
                self._check_error()
                raise RuntimeError("Search query failed")
            
            # Get results
            print("Debug: Getting search results", file=sys.stderr)
            num_results = min(self.dll.Everything_GetNumResults(), max_results)
            print (f"Debug: Number of results: {num_results}", file=sys.stderr)
            results = []

            filename_buffer = ctypes.create_unicode_buffer(260)
            date_created = ctypes.c_ulonglong()
            date_modified = ctypes.c_ulonglong()
            date_accessed = ctypes.c_ulonglong()
            file_size = ctypes.c_ulonglong()

            for i in range(num_results):
                try:
                    try:
                        self.dll.Everything_GetResultFullPathNameW(i, filename_buffer, 260)
                    except Exception as e:
                        print(f"Debug: Error getting full path name for result {i}: {e}", file=sys.stderr)
                        continue
                    
                    # Get timestamps
                    self.dll.Everything_GetResultDateCreated(i, date_created)
                    self.dll.Everything_GetResultDateModified(i, date_modified)
                    self.dll.Everything_GetResultDateAccessed(i, date_accessed)
                    self.dll.Everything_GetResultSize(i, file_size)
                    print (f"Debug: File size for result {i}: {file_size.value}", file=sys.stderr)
                    # Get other attributes
                    filename = self.dll.Everything_GetResultFileNameW(i)
                    extension = self.dll.Everything_GetResultExtensionW(i)
                    attributes = self.dll.Everything_GetResultAttributes(i)
                    run_count = self.dll.Everything_GetResultRunCount(i)
                    highlighted_filename = self.dll.Everything_GetResultHighlightedFileNameW(i)
                    highlighted_path = self.dll.Everything_GetResultHighlightedPathW(i)
                    print (f"Debug: Highlighted filename for result {i}: {highlighted_filename}", file=sys.stderr)


                    path=filename_buffer.value
                    print (f"Debug: Path for result {i}: {path}", file=sys.stderr)
                    try:
                        created=self._get_time(date_created.value).isoformat() if date_created.value else None
                    except Exception as e:
                        print(f"Debug: Error converting created time for result {i}: {e}", file=sys.stderr)
                        created = None
                    print (f"Debug: Created time for result {i}: {created}", file=sys.stderr)
                    try:
                        modified=self._get_time(date_modified.value).isoformat() if date_modified.value else None
                    except Exception as e:
                        print(f"Debug: Error converting modified time for result {i}: {e}", file=sys.stderr)
                        modified = None
                    print (f"Debug: Modified time for result {i}: {modified}", file=sys.stderr)
                    try:
                        accessed=self._get_time(date_accessed.value).isoformat() if date_accessed.value else None
                    except Exception as e:
                        print(f"Debug: Error converting accessed time for result {i}: {e}", file=sys.stderr)
                        accessed = None
                    print (f"Debug: Created time for result {i}: {created}", file=sys.stderr)   
                    try:
                        results.append(SearchResult(
                        path=path,
                        filename=filename,
                        extension=extension,
                        size=file_size.value,
                        created=created,
                        modified=modified,
                        accessed=accessed,
                        attributes=attributes,
                        run_count=run_count,
                        highlighted_filename=highlighted_filename,
                        highlighted_path=highlighted_path
                    ))
                    except Exception as e:
                        print(f"Debug: Error creating SearchResult for result {i}: {e}", file=sys.stderr)
                        continue
                except Exception as e:
                    print(f"Debug: Error processing result {i}: {e}", file=sys.stderr)
                    continue

            print("Debug: Resetting Everything SDK", file=sys.stderr)
            self.dll.Everything_Reset()

            return results