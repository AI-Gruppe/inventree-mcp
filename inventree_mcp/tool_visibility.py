"""Filter tools/list results down to what the current caller can actually use.

Every tool remains registered, but tools/list only advertises tools whose
underlying InvenTree API permission check succeeds for the method the tool
actually executes. Read tools are checked with GET; write tools are checked
with POST and are additionally hidden while MCP_READ_ONLY is enabled.

This is discovery-time convenience, not the security boundary:
proxy.call_view() still performs the real authenticated API dispatch and
enforces MCP_READ_ONLY on every tool invocation, even if a client calls a
hidden tool by name. Permission discovery deliberately uses the actual HTTP
method rather than OPTIONS so InvenTree's RolePermission and OAuth2 scope
mapping evaluate the same resource-specific permission as the eventual call.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from asgiref.sync import sync_to_async

from mcp.types import ListToolsResult, PaginatedRequestParams

from . import proxy
from .context import has_bound_identity, has_current_user
from .mcp_server import mcp
from .settings import get_plugin_setting
from .tools.discovery import RESOURCE_LOADERS

if TYPE_CHECKING:
    from mcp.server.context import ServerRequestContext

# Maps every gated tool name to the discovery.py resource key whose List
# view's GET permission determines whether it's shown. list_X/get_X
# deliberately share one entry: InvenTree's per-resource permission (role or
# OAuth2 scope) doesn't vary between a resource's List and Detail view in
# practice, and checking only the List view halves the number of real
# permission checks a single tools/list call has to run. A tool with no
# entry here (e.g. describe_filters - pure metadata, no underlying view) is
# always shown, and so is any *future* tool accidentally left out of this
# map - see test_every_gated_tool_has_a_visibility_entry in test_mcp.py for
# why an omission fails loudly instead of silently either hiding or
# over-exposing a tool.
_TOOL_RESOURCES: dict[str, str] = {
    "list_parts": "part",
    "get_part": "part",
    "list_categories": "category",
    "get_category": "category",
    "list_stock_items": "stock",
    "get_stock_item": "stock",
    "list_locations": "location",
    "get_location": "location",
    "list_purchase_orders": "purchase_order",
    "get_purchase_order": "purchase_order",
    "list_purchase_order_lines": "purchase_order_line",
    "get_purchase_order_line": "purchase_order_line",
    "list_sales_orders": "sales_order",
    "get_sales_order": "sales_order",
    "create_sales_order": "sales_order",
    "list_sales_order_lines": "sales_order_line",
    "get_sales_order_line": "sales_order_line",
    "create_sales_order_line": "sales_order_line",
    "list_sales_order_allocations": "sales_order_allocation",
    "get_sales_order_allocation": "sales_order_allocation",
    "list_build_orders": "build_order",
    "get_build_order": "build_order",
    "list_build_lines": "build_line",
    "get_build_line": "build_line",
    "list_build_items": "build_item",
    "get_build_item": "build_item",
    "list_companies": "company",
    "get_company": "company",
    "list_contacts": "contact",
    "get_contact": "contact",
    "list_addresses": "address",
    "get_address": "address",
    "list_manufacturer_parts": "manufacturer_part",
    "get_manufacturer_part": "manufacturer_part",
    "list_supplier_parts": "supplier_part",
    "get_supplier_part": "supplier_part",
    "list_bom_items": "bom_item",
    "get_bom_item": "bom_item",
    "list_bom_substitutes": "bom_substitute",
    "get_bom_substitute": "bom_substitute",
    "list_attachments": "attachment",
    "get_attachment": "attachment",
    "list_parameters": "parameter",
    "get_parameter": "parameter",
    "list_parameter_templates": "parameter_template",
    "get_parameter_template": "parameter_template",
    "list_return_orders": "return_order",
    "get_return_order": "return_order",
    "list_return_order_lines": "return_order_line",
    "get_return_order_line": "return_order_line",
    "list_stock_tracking": "stock_tracking",
    "get_stock_tracking": "stock_tracking",
    "list_stock_test_results": "stock_test_result",
    "get_stock_test_result": "stock_test_result",
    "list_project_codes": "project_code",
    "get_project_code": "project_code",
}

# Most tools are reads. Write tools explicitly declare the HTTP method whose
# real InvenTree permission check must succeed before they are advertised.
_TOOL_METHODS: dict[str, str] = {
    "create_sales_order": "POST",
    "create_sales_order_line": "POST",
}

# These mutation tools dispatch to a registry-selected resource/action based on
# their arguments, so they cannot be permission-filtered to one resource at
# tools/list time. They are advertised only to authenticated callers; the
# selected InvenTree view performs the real permission check at execution.
_MUTATION_DISPATCH_TOOLS = {
    "create_resource",
    "update_resource",
    "delete_resource",
    "invoke_action",
}


async def visible_tool_names(names: Iterable[str]) -> set[str]:
    """Return the subset of *names* the current bound user can actually call.

    A tool with no entry in _TOOL_RESOURCES (e.g. describe_filters) is
    always included - it has no underlying view to check a permission
    against, so this holds even for an unauthenticated caller (see below).
    If there's no request at all (e.g. static introspection outside a real
    MCP request - see OutputSchemaTest in test_mcp.py, which calls
    mcp.list_tools() directly without binding an identity), every name is
    returned unfiltered, since there's no caller to filter *by* - this is
    not a real request path, so there's nothing unsafe about it.

    A real request that resolved to an unauthenticated identity (e.g.
    REQUIRE_AUTH disabled and no credentials were sent) is deliberately
    *not* treated the same as "no request" above - has_bound_identity()
    (not has_current_user()) gates the unfiltered fallback, so this case
    falls through into the per-tool loop below instead. Every gated tool
    then correctly resolves to "not visible" (proxy.user_has_access()
    catches get_current_user()'s PermissionError for an unauthenticated
    caller and returns False), leaving only the tools with no underlying
    view at all visible - not the "no *role* required, but still needs to
    be someone" tools like list_attachments.
    """
    if not has_bound_identity():
        return set(names)

    visible: set[str] = set()
    resource_access: dict[tuple[str, str], bool] = {}
    read_only = await sync_to_async(get_plugin_setting)("MCP_READ_ONLY")

    for name in names:
        if name in _MUTATION_DISPATCH_TOOLS:
            if has_current_user() and not read_only:
                visible.add(name)
            continue

        resource = _TOOL_RESOURCES.get(name)
        if resource is None:
            visible.add(name)
            continue

        method = _TOOL_METHODS.get(name, "GET")
        if method != "GET" and read_only:
            continue

        access_key = (resource, method)
        if access_key not in resource_access:
            view_cls = RESOURCE_LOADERS[resource]()
            resource_access[access_key] = view_cls is not None and (
                await proxy.user_has_access(view_cls, method)
            )

        if resource_access[access_key]:
            visible.add(name)

    return visible


def apply() -> None:
    """Make the real (low-level, transport-facing) tools/list handler permission-aware.

    MCPServer.list_tools() is left untouched as an attribute - it's reassigned
    *around*, not in place, specifically so existing tests that call
    mcp.list_tools() directly to introspect the full, unfiltered registry
    (e.g. "every tool has an output_schema") keep working unchanged. What
    this actually overrides is the low-level mcp.server.lowlevel.Server's
    registered "tools/list" request handler - the thing a real client's
    tools/list request reaches over the wire (see mcp_transport.py) - by
    re-registering it via add_request_handler(), the same "no public API for
    this, reach into internals" approach output_schemas.apply() already uses
    for a different MCPServer internal. mcp 2.0's rewrite replaced the
    lowlevel Server's decorator-based `.list_tools()` registration with
    add_request_handler(method, params_type, handler) - the handler itself
    now takes (ctx, params) and must return a ListToolsResult, rather than a
    bare list[Tool].
    """
    unfiltered_list_tools = mcp.list_tools

    async def filtered_list_tools(
        ctx: ServerRequestContext, params: PaginatedRequestParams | None
    ) -> ListToolsResult:
        tools = await unfiltered_list_tools()
        names = await visible_tool_names(tool.name for tool in tools)
        return ListToolsResult(tools=[tool for tool in tools if tool.name in names])

    mcp._lowlevel_server.add_request_handler(
        "tools/list", PaginatedRequestParams, filtered_list_tools
    )
