"""Regression tests for the platform tool-input schema.

Covers the bug where Pydantic emitted the ``WindowsSortOption`` enum as a
``$ref`` to a ``$defs`` block nested *inside* ``windows_params``. A JSON
Schema ``$ref`` of ``#/$defs/...`` resolves from the document root, so the
nested placement left a dangling pointer and MCP clients rejected the tool
input with ``PointerToNowhere``.
"""

from mcp_server_everything_search.platform_search import UnifiedSearchQuery


def _iter_refs(node):
    """Yield every ``$ref`` string found anywhere in a schema fragment."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "$ref" and isinstance(value, str):
                yield value
            else:
                yield from _iter_refs(value)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_refs(item)


def _resolve(root, ref):
    """Resolve a ``#/a/b/c`` JSON pointer against the document root."""
    assert ref.startswith("#/"), f"unexpected $ref form: {ref}"
    target = root
    for part in ref[2:].split("/"):
        target = target[part]  # KeyError here == dangling pointer
    return target


def test_all_refs_resolve_against_root():
    """Every $ref in the generated schema must resolve from the root."""
    schema = UnifiedSearchQuery.get_schema_for_platform()
    refs = list(_iter_refs(schema))
    for ref in refs:
        # Must not raise -- a dangling pointer is exactly the original bug.
        _resolve(schema, ref)


def test_defs_are_hoisted_to_root():
    """Nested $defs must be lifted to the root, none left inside properties."""
    schema = UnifiedSearchQuery.get_schema_for_platform()
    for name, prop in schema["properties"].items():
        assert "$defs" not in prop, f"{name} still carries a nested $defs"
