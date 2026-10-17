"""Behavioral tests for platform_search: parameter models, tool schema, commands.

The platform is an ambient input read through ``platform.system()``; tests
stub it so every platform's behavior is exercised on any host.
"""

import platform
from typing import Any, Dict, Iterator

import jsonschema
import pytest
from pydantic import ValidationError

from mcp_server_everything_search.platform_search import (
    BaseSearchQuery,
    LinuxSpecificParams,
    MacSpecificParams,
    UnifiedSearchQuery,
    WindowsSortOption,
    WindowsSpecificParams,
    build_search_command,
)

ALL_PLATFORMS = ["Windows", "Darwin", "Linux"]


@pytest.fixture
def on_platform(monkeypatch: pytest.MonkeyPatch):
    def _set(name: str) -> None:
        monkeypatch.setattr(platform, "system", lambda: name)

    return _set


def _subschemas(node: Any) -> Iterator[Dict[str, Any]]:
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _subschemas(value)
    elif isinstance(node, list):
        for item in node:
            yield from _subschemas(item)


def _property_schemas(schema: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    for sub in _subschemas(schema):
        props = sub.get("properties")
        if isinstance(props, dict):
            yield from props.values()


# --- Tool input schema (issues #16, #21, #26) ---


@pytest.mark.parametrize("system", ALL_PLATFORMS)
def test_schema_is_valid_json_schema_for_every_platform(on_platform, system):
    # Arrange
    on_platform(system)
    schema = UnifiedSearchQuery.get_schema_for_platform()

    # Act
    meta_validator = jsonschema.Draft202012Validator(
        jsonschema.Draft202012Validator.META_SCHEMA
    )
    errors = list(meta_validator.iter_errors(schema))

    # Assert
    assert errors == []


def test_windows_request_with_sort_by_validates_against_schema(on_platform):
    # Arrange
    on_platform("Windows")
    schema = UnifiedSearchQuery.get_schema_for_platform()
    request = {
        "base": {"query": "uvx.exe", "max_results": 10},
        "windows_params": {"match_case": False, "sort_by": 6},
    }

    # Act: raised PointerToNowhere before the fix
    errors = list(jsonschema.Draft202012Validator(schema).iter_errors(request))

    # Assert
    assert errors == []


def test_windows_request_with_unknown_sort_by_is_rejected_by_schema(on_platform):
    # Arrange
    on_platform("Windows")
    schema = UnifiedSearchQuery.get_schema_for_platform()
    request = {"base": {"query": "x"}, "windows_params": {"sort_by": 9}}

    # Act / Assert
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(request, schema)


def _is_typed(prop: Dict[str, Any]) -> bool:
    if "anyOf" in prop:
        return all("type" in branch for branch in prop["anyOf"])
    return "type" in prop


@pytest.mark.parametrize("system", ALL_PLATFORMS)
def test_every_schema_property_declares_a_type(on_platform, system):
    # Arrange
    on_platform(system)
    schema = UnifiedSearchQuery.get_schema_for_platform()

    # Act
    untyped = [p for p in _property_schemas(schema) if not _is_typed(p)]

    # Assert: Gemini CLI skips tools whose properties lack a type (#21)
    assert untyped == []


@pytest.mark.parametrize("system", ALL_PLATFORMS)
def test_schema_is_self_contained_without_refs_or_defs(on_platform, system):
    # Arrange
    on_platform(system)
    schema = UnifiedSearchQuery.get_schema_for_platform()

    # Act
    ref_keys = [k for sub in _subschemas(schema) for k in sub if k in ("$ref", "$defs")]

    # Assert: clients with limited $ref support can consume the schema
    assert ref_keys == []


_EXPECTED_PLATFORM_PROPERTY_TYPES = {
    "Windows": (
        "windows_params",
        {
            "match_path": "boolean",
            "match_case": "boolean",
            "match_whole_word": "boolean",
            "match_regex": "boolean",
            "sort_by": "integer",
        },
    ),
    "Darwin": (
        "mac_params",
        {
            "live_updates": "boolean",
            "search_directory": None,
            "literal_query": "boolean",
            "interpret_query": "boolean",
        },
    ),
    "Linux": (
        "linux_params",
        {
            "ignore_case": "boolean",
            "regex_search": "boolean",
            "existing_files": "boolean",
            "count_only": "boolean",
        },
    ),
}


@pytest.mark.parametrize("system", ALL_PLATFORMS)
def test_platform_params_schema_exposes_every_field_with_its_type(on_platform, system):
    # Arrange
    on_platform(system)
    key, expected = _EXPECTED_PLATFORM_PROPERTY_TYPES[system]

    # Act
    props = UnifiedSearchQuery.get_schema_for_platform()["properties"][key][
        "properties"
    ]

    # Assert
    assert set(props) == set(expected)
    for name, json_type in expected.items():
        if json_type is not None:
            assert props[name]["type"] == json_type, name


def test_mac_search_directory_schema_allows_string_or_null(on_platform):
    on_platform("Darwin")

    props = UnifiedSearchQuery.get_schema_for_platform()["properties"]["mac_params"][
        "properties"
    ]

    assert {b["type"] for b in props["search_directory"]["anyOf"]} == {"string", "null"}


def test_windows_sort_by_schema_lists_every_sort_option(on_platform):
    # Arrange
    on_platform("Windows")

    # Act
    schema = UnifiedSearchQuery.get_schema_for_platform()
    sort_by = schema["properties"]["windows_params"]["properties"]["sort_by"]

    # Assert
    assert sort_by["type"] == "integer"
    assert sorted(sort_by["enum"]) == sorted(o.value for o in WindowsSortOption)
    assert sort_by["default"] == WindowsSortOption.NAME_ASC.value
    assert sort_by["description"] == "Sort order for results"


@pytest.mark.parametrize(
    ("system", "platform_key"),
    [
        ("Windows", "windows_params"),
        ("Darwin", "mac_params"),
        ("Linux", "linux_params"),
    ],
)
def test_schema_exposes_base_and_only_current_platform_params(
    on_platform, system, platform_key
):
    # Arrange
    on_platform(system)

    # Act
    schema = UnifiedSearchQuery.get_schema_for_platform()

    # Assert
    assert schema["type"] == "object"
    assert schema["required"] == ["base"]
    assert set(schema["properties"]) == {"base", platform_key}
    assert schema["properties"]["base"]["required"] == ["query"]


def test_schema_on_unsupported_platform_exposes_only_base(on_platform):
    # Arrange
    on_platform("SunOS")

    # Act
    schema = UnifiedSearchQuery.get_schema_for_platform()

    # Assert
    assert set(schema["properties"]) == {"base"}


# --- Parameter models ---


def test_base_query_defaults_max_results_to_100():
    query = BaseSearchQuery(query="report")

    assert query.query == "report"
    assert query.max_results == 100


@pytest.mark.parametrize("max_results", [0, 1001])
def test_base_query_rejects_max_results_outside_1_to_1000(max_results):
    with pytest.raises(ValidationError):
        BaseSearchQuery(query="report", max_results=max_results)


def test_mac_params_defaults_disable_every_option():
    params = MacSpecificParams()

    assert params.live_updates is False
    assert params.search_directory is None
    assert params.literal_query is False
    assert params.interpret_query is False


def test_linux_params_defaults_ignore_case_and_existing_files_only():
    params = LinuxSpecificParams()

    assert params.ignore_case is True
    assert params.regex_search is False
    assert params.existing_files is True
    assert params.count_only is False


def test_windows_params_defaults_to_name_ascending_with_matching_off():
    params = WindowsSpecificParams()

    assert params.match_path is False
    assert params.match_case is False
    assert params.match_whole_word is False
    assert params.match_regex is False
    assert params.sort_by is WindowsSortOption.NAME_ASC


def test_windows_params_accepts_integer_sort_option():
    params = WindowsSpecificParams.model_validate({"sort_by": 6})

    assert params.sort_by is WindowsSortOption.SIZE_DESC
    assert params.sort_by == 6


def test_windows_params_rejects_unknown_sort_option():
    with pytest.raises(ValidationError):
        WindowsSpecificParams.model_validate({"sort_by": 9})


def test_windows_sort_option_values_match_everything_sdk_sort_codes():
    assert {o.name: o.value for o in WindowsSortOption} == {
        "NAME_ASC": 1,
        "NAME_DESC": 2,
        "PATH_ASC": 3,
        "PATH_DESC": 4,
        "SIZE_ASC": 5,
        "SIZE_DESC": 6,
        "EXT_ASC": 7,
        "EXT_DESC": 8,
        "CREATED_ASC": 11,
        "CREATED_DESC": 12,
        "MODIFIED_ASC": 13,
        "MODIFIED_DESC": 14,
    }


# --- Platform parameter selection ---


@pytest.mark.parametrize(
    ("system", "expected_attr"),
    [
        ("Windows", "windows_params"),
        ("Darwin", "mac_params"),
        ("Linux", "linux_params"),
    ],
)
def test_get_platform_params_returns_current_platform_params(
    on_platform, system, expected_attr
):
    # Arrange
    query = UnifiedSearchQuery(
        query="x",
        windows_params=WindowsSpecificParams(),
        mac_params=MacSpecificParams(),
        linux_params=LinuxSpecificParams(),
    )
    on_platform(system)

    # Act
    result = query.get_platform_params()

    # Assert
    assert result is getattr(query, expected_attr)


def test_get_platform_params_on_unsupported_platform_returns_none(on_platform):
    query = UnifiedSearchQuery(query="x", linux_params=LinuxSpecificParams())
    on_platform("SunOS")

    assert query.get_platform_params() is None


# --- Command building ---


def test_build_command_darwin_maps_every_mac_option(on_platform):
    # Arrange
    on_platform("Darwin")
    query = UnifiedSearchQuery(
        query="kind:pdf",
        mac_params=MacSpecificParams(
            live_updates=True,
            search_directory="/Users/me",
            literal_query=True,
            interpret_query=True,
        ),
    )

    # Act
    cmd = build_search_command(query)

    # Assert
    assert cmd == [
        "mdfind",
        "-live",
        "-onlyin",
        "/Users/me",
        "-literal",
        "-interpret",
        "kind:pdf",
    ]


def test_build_command_darwin_without_params_is_plain_mdfind(on_platform):
    on_platform("Darwin")

    assert build_search_command(UnifiedSearchQuery(query="notes")) == [
        "mdfind",
        "notes",
    ]


def test_build_command_linux_default_params_add_ignore_case_and_existing(on_platform):
    on_platform("Linux")
    query = UnifiedSearchQuery(query="*.py", linux_params=LinuxSpecificParams())

    assert build_search_command(query) == ["locate", "-i", "-e", "*.py"]


def test_build_command_linux_maps_regex_and_count(on_platform):
    on_platform("Linux")
    query = UnifiedSearchQuery(
        query="^/etc",
        linux_params=LinuxSpecificParams(
            ignore_case=False, regex_search=True, existing_files=False, count_only=True
        ),
    )

    assert build_search_command(query) == ["locate", "-r", "-c", "^/etc"]


def test_build_command_linux_without_params_is_plain_locate(on_platform):
    on_platform("Linux")

    assert build_search_command(UnifiedSearchQuery(query="notes")) == [
        "locate",
        "notes",
    ]


def test_build_command_windows_returns_empty_list(on_platform):
    on_platform("Windows")

    assert build_search_command(UnifiedSearchQuery(query="notes")) == []


def test_build_command_unsupported_platform_raises(on_platform):
    on_platform("SunOS")

    with pytest.raises(NotImplementedError):
        build_search_command(UnifiedSearchQuery(query="notes"))
