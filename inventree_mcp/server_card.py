"""Serve an MCP Server Card for discoverability.

Implements SEP-2127 (https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2127),
which lets an MCP client discover this server's remote endpoint and supported
protocol versions ahead of connecting, without guessing or hardcoding a URL.

The card deliberately omits tools/resources/prompts - those are dynamic
(vary by caller's role/OAuth2 scope, see tool_visibility.py) and already
discoverable at runtime via the real MCP `tools/list` call.

This view is registered as a plain plugin URL regardless of InvenTree
version (see core.py's setup_urls()), so it's always directly reachable.
It's only *advertised* under /.well-known/ when the running InvenTree
provides WellKnownMixin - see _well_known_compat.py.
"""

from __future__ import annotations

from django.http import HttpRequest, JsonResponse
from django.urls import path, reverse
from InvenTree.permissions import auth_exempt
from mcp_types.version import SUPPORTED_PROTOCOL_VERSIONS

from . import PLUGIN_VERSION

# Must be exactly this URL per SEP-2127.
SERVER_CARD_SCHEMA = (
    "https://static.modelcontextprotocol.io/schemas/v1/server-card.schema.json"
)


def build_server_card(request: HttpRequest) -> dict:
    """Build this plugin's MCP Server Card document."""
    mcp_url = request.build_absolute_uri(reverse("plugin:inventree-mcp:mcp-endpoint"))

    return {
        "$schema": SERVER_CARD_SCHEMA,
        "name": "io.github.inventree/inventree-mcp",
        "version": PLUGIN_VERSION,
        "title": "InvenTree MCP",
        "description": "MCP server for InvenTree",
        "websiteUrl": "https://github.com/inventree/inventree-mcp",
        "repository": {
            "url": "https://github.com/inventree/inventree-mcp",
            "source": "github",
        },
        "remotes": [
            {
                "type": "streamable-http",
                "url": mcp_url,
                "supportedProtocolVersions": list(SUPPORTED_PROTOCOL_VERSIONS),
            }
        ],
    }


@auth_exempt
def view_server_card(request: HttpRequest) -> JsonResponse:
    """Return this plugin's MCP Server Card as JSON.

    Deliberately unauthenticated, unlike the real MCP endpoint - this is
    discovery metadata only (no InvenTree data), matching the passkey-endpoints
    well-known view InvenTree ships built-in (core_wellknown.py).
    """
    return JsonResponse(build_server_card(request))


urlpatterns = [path("server-card/", view_server_card, name="server-card")]
