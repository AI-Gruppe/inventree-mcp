# InvenTreeMCP

[![PyPI](https://img.shields.io/pypi/v/inventree-mcp)](https://pypi.org/project/inventree-mcp/)
[![CI](https://github.com/inventree/inventree-mcp/actions/workflows/ci.yaml/badge.svg)](https://github.com/inventree/inventree-mcp/actions/workflows/ci.yaml)
[![codecov](https://codecov.io/gh/inventree/inventree-mcp/graph/badge.svg)](https://codecov.io/gh/inventree/inventree-mcp)

An MCP (Model Context Protocol) server for InvenTree, exposed as an InvenTree plugin. It lets MCP
clients (Claude, other MCP-aware agents) query InvenTree inventory data over a Streamable HTTP
endpoint.

## Design

Every tool is a thin wrapper around InvenTree's own REST API view classes (see
[`inventree_mcp/proxy.py`](inventree_mcp/proxy.py)), dispatched as the authenticated caller - MCP
requests go through exactly the same permission checks, filtering, and serialization as the regular
REST API. Tool code never queries the Django ORM directly.

Read tools cover parts, stock items/locations, part categories, purchase/sales/return/build orders
(with line items and allocations), companies, contacts, addresses, manufacturer/supplier parts,
BOM items, attachments, parameters, stock tracking history, test results, and project codes.

Write support is registry-backed and broad. Use `describe_resource(resource)` to discover
the create / PATCH-update / delete / bulk operations and domain actions available for a resource,
including serializer-derived writable fields and caller-specific permission checks. Mutations are
performed with `create_resource`, `update_resource`, `delete_resource`,
`bulk_update_resource`, `bulk_delete_resource`, and `invoke_action`.

The mutation registry covers operational InvenTree resources including parts/categories/BOMs,
stock and locations, companies and catalog parts, purchase/sales/return/transfer orders and their
lines, shipments/allocations, build orders, parameters, attachments, notes, project codes, tags,
price breaks and related resources. Domain actions cover order lifecycle transitions and
receive/allocate/ship flows, stock adjustments/transfers/serialization, build allocation/consume/
output workflows, and BOM validation/copy operations. Authentication / OAuth application
administration endpoints are deliberately not exposed through this mutation registry.

`MCP_READ_ONLY` is disabled by default. Enabling it hides and blocks all mutation tools.
Normal InvenTree role and OAuth2-scope checks still apply to every mutation because every call is
dispatched through InvenTree's real DRF view.

Each tool's `outputSchema` and filter/ordering options are derived live from InvenTree's own
serializers and views (not hand-maintained), so they can't drift as InvenTree evolves. Call
`describe_filters(resource)` to see what's available for a given resource. The set of tools an MCP
client sees is also filtered to what the calling user can actually use - though every call is still
permission-checked in full regardless of what was advertised.

## Setup

### 1. Install the plugin

Install via the InvenTree plugin manager, or via pip:

```bash
pip install inventree-mcp
```

Then enable the plugin under **Admin > Plugins**, and configure its settings (see
Configuration below).

### 2. Create a token for your MCP client

Create an InvenTree API token for your MCP client.

### 3. Configure your MCP client

The endpoint is `<your-inventree-server>/plugin/inventree-mcp/mcp/`, using Streamable HTTP
transport with an `Authorization: Token <token>` header.

For a client that supports remote Streamable HTTP servers directly, add:

```json
{
  "mcpServers": {
    "inventree": {
      "url": "https://<your-inventree-server>/plugin/inventree-mcp/mcp/",
      "headers": {
        "Authorization": "Token <your-api-token>"
      }
    }
  }
}
```

For a client that only supports local (stdio) servers, bridge it with
[`mcp-remote`](https://www.npmjs.com/package/mcp-remote)

*Note: You will need to have node available on your system path*

```json
{
  "mcpServers": {
    "inventree": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote@latest",
        "https://<your-inventree-server>/plugin/inventree-mcp/mcp/",
        "--header",
        "Authorization: Token <your-api-token>"
      ]
    }
  }
}
```

*Note: On Windows, you may need to substitute `npx` with `C:\\PROGRA~1\\nodejs\\npx.cmd` in the command field.*

In a setup where the server is running a self-signed certificate, you may need to use the following `env` arguments to disable certificate verification:

```json
"args": [
  ...
],
"env": {
  "NODE_TLS_REJECT_UNAUTHORIZED": "0"
}
```

## Configuration

Under **Settings > Plugin Settings**:

- **Require Authentication** (`REQUIRE_AUTH`, default `True`): reject unauthenticated requests.
  Only disable for local testing.
- **Read Only** (`MCP_READ_ONLY`, default `False`): when enabled, block all write actions via MCP,
  regardless of the calling user's permissions. A plugin-wide kill switch, independent of per-user roles.

## Authentication

Access follows the calling user's normal InvenTree role assignments. Supported auth methods:

- An InvenTree API token: `Authorization: Token <token>`.
- Basic auth (username/password).
- An OAuth2 bearer token: `Authorization: Bearer <token>`. A scoped token (e.g. `r:view:part`)
  narrows access *below* the underlying user's roles - useful for issuing an agent a tightly-scoped
  token without creating a separate low-privilege user.

Session/cookie auth is not supported (not meaningful for a machine client).
