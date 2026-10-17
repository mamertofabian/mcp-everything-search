"""Platform-specific search implementations with dedicated parameter models."""

from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field
from enum import Enum
import platform


class BaseSearchQuery(BaseModel):
    """Base search parameters common to all platforms."""

    query: str = Field(
        description="Search query string. See platform-specific documentation for syntax details."
    )
    max_results: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of results to return (1-1000)",
    )


class MacSpecificParams(BaseModel):
    """macOS-specific search parameters for mdfind."""

    live_updates: bool = Field(
        default=False, description="Provide live updates to search results"
    )
    search_directory: Optional[str] = Field(
        default=None,
        description="Limit search to specific directory (-onlyin parameter)",
    )
    literal_query: bool = Field(
        default=False,
        description="Treat query as literal string without interpretation",
    )
    interpret_query: bool = Field(
        default=False, description="Interpret query as if typed in Spotlight menu"
    )


class LinuxSpecificParams(BaseModel):
    """Linux-specific search parameters for locate."""

    ignore_case: bool = Field(
        default=True, description="Ignore case distinctions (-i parameter)"
    )
    regex_search: bool = Field(
        default=False, description="Use regular expressions in patterns (-r parameter)"
    )
    existing_files: bool = Field(
        default=True, description="Only output existing files (-e parameter)"
    )
    count_only: bool = Field(
        default=False, description="Only display count of matches (-c parameter)"
    )


class WindowsSortOption(int, Enum):
    """Sort options for Windows Everything search."""

    NAME_ASC = 1
    NAME_DESC = 2
    PATH_ASC = 3
    PATH_DESC = 4
    SIZE_ASC = 5
    SIZE_DESC = 6
    EXT_ASC = 7
    EXT_DESC = 8
    CREATED_ASC = 11
    CREATED_DESC = 12
    MODIFIED_ASC = 13
    MODIFIED_DESC = 14


class WindowsSpecificParams(BaseModel):
    """Windows-specific search parameters for Everything SDK."""

    match_path: bool = Field(
        default=False, description="Match against full path instead of filename only"
    )
    match_case: bool = Field(default=False, description="Enable case-sensitive search")
    match_whole_word: bool = Field(default=False, description="Match whole words only")
    match_regex: bool = Field(default=False, description="Enable regex search")
    sort_by: WindowsSortOption = Field(
        default=WindowsSortOption.NAME_ASC, description="Sort order for results"
    )


_LOCAL_DEF_PREFIX = "#/$defs/"


def _inline_local_refs(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of a Pydantic model schema with local $refs inlined.

    Sub-schemas are embedded under the tool schema's properties, where a
    "#/$defs/..." pointer would resolve against the tool schema root and
    dangle. Inlining also gives every property its own "type", which clients
    such as Gemini CLI require. Keys on the referencing property (description,
    default) take precedence over the definition's; the definition title is
    dropped.
    """
    defs: Dict[str, Any] = schema.get("$defs", {})

    def resolve(node: Any, seen: Tuple[str, ...]) -> Any:
        if isinstance(node, list):
            return [resolve(item, seen) for item in node]
        if not isinstance(node, dict):
            return node
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith(_LOCAL_DEF_PREFIX):
            name = ref[len(_LOCAL_DEF_PREFIX) :]
            if name in seen:
                raise ValueError(f"Recursive schema reference cannot be inlined: {ref}")
            if name not in defs:
                raise ValueError(f"Schema reference has no matching definition: {ref}")
            definition = {k: v for k, v in defs[name].items() if k != "title"}
            siblings = {k: v for k, v in node.items() if k != "$ref"}
            return {**resolve(definition, seen + (name,)), **resolve(siblings, seen)}
        return {k: resolve(v, seen) for k, v in node.items() if k != "$defs"}

    return resolve(schema, ())


class UnifiedSearchQuery(BaseSearchQuery):
    """Combined search parameters model."""

    mac_params: Optional[MacSpecificParams] = None
    linux_params: Optional[LinuxSpecificParams] = None
    windows_params: Optional[WindowsSpecificParams] = None

    @classmethod
    def get_schema_for_platform(cls) -> Dict[str, Any]:
        """Get the appropriate schema based on the current platform."""
        system = platform.system().lower()

        schema = {
            "type": "object",
            "properties": {
                "base": _inline_local_refs(BaseSearchQuery.model_json_schema())
            },
            "required": ["base"],
        }

        # Add platform-specific parameters
        if system == "darwin":
            schema["properties"]["mac_params"] = _inline_local_refs(
                MacSpecificParams.model_json_schema()
            )
        elif system == "linux":
            schema["properties"]["linux_params"] = _inline_local_refs(
                LinuxSpecificParams.model_json_schema()
            )
        elif system == "windows":
            schema["properties"]["windows_params"] = _inline_local_refs(
                WindowsSpecificParams.model_json_schema()
            )

        return schema

    def get_platform_params(self) -> Optional[BaseModel]:
        """Get the parameters specific to the current platform."""
        system = platform.system().lower()
        if system == "darwin":
            return self.mac_params
        elif system == "linux":
            return self.linux_params
        elif system == "windows":
            return self.windows_params
        return None


def build_search_command(query: UnifiedSearchQuery) -> List[str]:
    """Build the appropriate search command based on platform and parameters."""
    system = platform.system().lower()
    platform_params = query.get_platform_params()

    if system == "darwin":
        cmd = ["mdfind"]
        if isinstance(platform_params, MacSpecificParams):
            if platform_params.live_updates:
                cmd.append("-live")
            if platform_params.search_directory:
                cmd.extend(["-onlyin", platform_params.search_directory])
            if platform_params.literal_query:
                cmd.append("-literal")
            if platform_params.interpret_query:
                cmd.append("-interpret")
        cmd.append(query.query)  # Use query directly from UnifiedSearchQuery
        return cmd

    elif system == "linux":
        cmd = ["locate"]
        if isinstance(platform_params, LinuxSpecificParams):
            if platform_params.ignore_case:
                cmd.append("-i")
            if platform_params.regex_search:
                cmd.append("-r")
            if platform_params.existing_files:
                cmd.append("-e")
            if platform_params.count_only:
                cmd.append("-c")
        cmd.append(query.query)  # Use query directly from UnifiedSearchQuery
        return cmd

    elif system == "windows":
        # Windows uses the Everything SDK directly, so there is no command to run
        return []

    raise NotImplementedError(f"Unsupported platform: {system}")
