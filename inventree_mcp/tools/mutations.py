"""Generic mutation tools backed by an explicit InvenTree capability registry."""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver.exceptions import ToolError

from .. import proxy
from ..mcp_server import mcp
from ..mutation_registry import ACTIONS, RESOURCES, ActionSpec, ResourceSpec
from ..schema_introspection import writable_serializer_schema


def _resource(name: str) -> ResourceSpec:
    spec = RESOURCES.get(name)
    if spec is None:
        raise ToolError(
            f"Unknown resource {name!r}. Choose one of: {', '.join(sorted(RESOURCES))}"
        )
    return spec


def _action(name: str) -> ActionSpec:
    spec = ACTIONS.get(name)
    if spec is None:
        raise ToolError(
            f"Unknown action {name!r}. Choose one of: {', '.join(sorted(ACTIONS))}"
        )
    return spec


def _serializer_class(view_cls: type | None, action: str | None = None):
    """Resolve the serializer used by a regular view or DRF custom action."""
    if view_cls is None:
        return None

    if action and hasattr(view_cls, action):
        fn = getattr(view_cls, action)
        kwargs = getattr(fn, "kwargs", {}) or {}
        serializer_class = kwargs.get("serializer_class")
        if serializer_class is not None:
            return serializer_class

    return getattr(view_cls, "serializer_class", None)


def _input_schema(
    view_cls: type | None,
    *,
    partial: bool = False,
    action: str | None = None,
):
    serializer_class = _serializer_class(view_cls, action)
    if serializer_class is None:
        return {"type": "object", "additionalProperties": True}
    return writable_serializer_schema(serializer_class, partial=partial)


@mcp.tool()
async def describe_resource(resource: str) -> dict:
    """Describe mutation capabilities and writable fields for a resource.

    This is the mutation counterpart to describe_filters. It reports only
    registry-backed operations and actions, along with schemas derived from
    the real InvenTree serializers. Permission booleans reflect the caller.
    """
    spec = _resource(resource)
    list_view = spec.list_loader()
    detail_view = spec.detail_loader() if spec.detail_loader else None

    operations: dict[str, Any] = {}

    if spec.create:
        operations["create"] = {
            "allowed": list_view is not None
            and await proxy.user_has_access(list_view, "POST"),
            "input_schema": _input_schema(list_view),
        }

    if spec.update and detail_view is not None:
        operations["update"] = {
            "allowed": await proxy.user_has_access(detail_view, "PATCH"),
            "input_schema": _input_schema(detail_view, partial=True),
        }

    if spec.delete and detail_view is not None:
        operations["delete"] = {
            "allowed": await proxy.user_has_access(detail_view, "DELETE"),
            "input_schema": {"type": "object", "additionalProperties": True},
        }

    actions: dict[str, Any] = {}
    prefix = resource + "."
    for name, action_spec in ACTIONS.items():
        if action_spec.resource != resource and not name.startswith(prefix):
            continue

        view_cls = action_spec.loader()
        actions[name] = {
            "allowed": view_cls is not None
            and await proxy.user_has_access(view_cls, action_spec.method),
            "requires_id": action_spec.id_arg is not None,
            "input_schema": _input_schema(
                view_cls, action=action_spec.viewset_action
            ),
        }

    return {
        "resource": resource,
        "operations": operations,
        "actions": actions,
    }


@mcp.tool()
async def create_resource(resource: str, data: dict[str, Any]) -> dict:
    """Create a registered InvenTree resource through its real REST view."""
    spec = _resource(resource)
    if not spec.create:
        raise ToolError(f"Resource {resource!r} does not support direct creation")

    return await proxy.call_view(
        spec.list_loader(),
        "POST",
        spec.list_path,
        data=data,
    )


@mcp.tool()
async def update_resource(
    resource: str,
    resource_id: int,
    data: dict[str, Any],
) -> dict:
    """Partially update a registered InvenTree resource using PATCH."""
    spec = _resource(resource)
    if not spec.update or spec.detail_loader is None or spec.detail_path is None:
        raise ToolError(f"Resource {resource!r} does not support direct updates")

    return await proxy.call_view(
        spec.detail_loader(),
        "PATCH",
        spec.detail_path.format(id=resource_id),
        data=data,
        pk=resource_id,
    )


@mcp.tool()
async def delete_resource(
    resource: str,
    resource_id: int,
    data: dict[str, Any] | None = None,
) -> dict:
    """Delete a registered resource through its real REST endpoint."""
    spec = _resource(resource)
    if not spec.delete or spec.detail_loader is None or spec.detail_path is None:
        raise ToolError(f"Resource {resource!r} does not support direct deletion")

    return await proxy.call_view(
        spec.detail_loader(),
        "DELETE",
        spec.detail_path.format(id=resource_id),
        data=data or {},
        pk=resource_id,
    )


@mcp.tool()
async def invoke_action(
    action: str,
    resource_id: int | None = None,
    data: dict[str, Any] | None = None,
) -> dict:
    """Run an allowlisted InvenTree domain action.

    Examples include issuing or receiving orders, allocating stock, shipping
    a shipment, consuming build stock, transferring stock, and validating BOMs.
    Use describe_resource to discover actions and input schemas.
    """
    spec = _action(action)

    if spec.id_arg is not None and resource_id is None:
        raise ToolError(f"Action {action!r} requires resource_id")

    path = spec.path
    kwargs: dict[str, Any] = {}

    if spec.id_arg is not None:
        path = path.format(id=resource_id)
        kwargs[spec.id_arg] = resource_id

    return await proxy.call_view(
        spec.loader(),
        spec.method,
        path,
        data=data or {},
        viewset_action=spec.viewset_action,
        **kwargs,
    )
