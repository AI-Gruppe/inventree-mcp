"""Tests for opt-in MCP write tools."""

from __future__ import annotations

from typing import ClassVar

from asgiref.sync import sync_to_async
from company.models import Company
from django.contrib.auth import get_user_model
from django.test import override_settings
from InvenTree.unit_test import InvenTreeTestCase
from mcp.server.mcpserver.exceptions import ToolError
from part.models import Part
from plugin import registry

from . import context, tool_visibility
from .mcp_server import mcp
from .tools.sales_orders import create_sales_order, create_sales_order_line


@override_settings(PLUGIN_TESTING_SETUP=True)
class MCPWriteToolTest(InvenTreeTestCase):
    """Verify sales-order writes remain explicit, permission-safe, and opt-in."""

    roles: ClassVar[list[str]] = ["sales_order.view"]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.customer = Company.objects.create(
            name="MCP Write Customer", is_customer=True, is_supplier=False
        )
        cls.part = Part.objects.create(
            name="MCP Write Part",
            description="Part used by MCP write tests",
            salable=True,
        )
        cls.no_access_user = get_user_model().objects.create_user(
            username="mcp-write-no-access",
            password="mcp-write-no-access",
        )

        registry.reload_plugins(full_reload=True, collect=True)
        registry.set_plugin_state("inventree-mcp", True)

    def _as(self, user):
        context.set_current_user(user)
        self.addCleanup(context.set_current_user, None)

    async def _disable_read_only(self):
        def _disable():
            plugin = registry.get_plugin("inventree-mcp")
            plugin.set_setting("MCP_READ_ONLY", False)
            return plugin

        plugin = await sync_to_async(_disable)()
        self.addCleanup(plugin.set_setting, "MCP_READ_ONLY", True)

    async def _grant_add_role(self):
        await sync_to_async(self.assignRole)(
            role="sales_order.add", group=self.group
        )

    async def test_write_tools_are_blocked_in_read_only_mode(self):
        self._as(self.user)

        with self.assertRaises(ToolError) as cm:
            await create_sales_order(
                reference="SO-MCP-WRITE-001",
                customer=self.customer.pk,
            )

        self.assertIn("read-only", str(cm.exception).lower())

    async def test_authorized_user_can_create_order_and_line(self):
        await self._grant_add_role()
        await self._disable_read_only()
        self._as(self.user)

        order = await create_sales_order(
            reference="SO-MCP-WRITE-002",
            customer=self.customer.pk,
            description="Created through MCP",
        )

        self.assertEqual(order["reference"], "SO-MCP-WRITE-002")
        self.assertEqual(order["customer"], self.customer.pk)

        line = await create_sales_order_line(
            order=order["pk"],
            part=self.part.pk,
            quantity=3,
            reference="MCP-LINE-1",
        )

        self.assertEqual(line["order"], order["pk"])
        self.assertEqual(line["part"], self.part.pk)
        self.assertEqual(float(line["quantity"]), 3.0)

    async def test_invalid_write_uses_real_serializer_validation(self):
        await self._grant_add_role()
        await self._disable_read_only()
        self._as(self.user)

        with self.assertRaises(ToolError):
            await create_sales_order(
                reference="SO-MCP-WRITE-003",
                customer=999999999,
            )

    async def test_user_without_add_permission_cannot_write(self):
        await self._disable_read_only()
        self._as(self.no_access_user)

        with self.assertRaises(ToolError):
            await create_sales_order(
                reference="SO-MCP-WRITE-004",
                customer=self.customer.pk,
            )

    async def test_visibility_hides_writes_until_enabled_and_permitted(self):
        self._as(self.user)
        all_names = {tool.name for tool in await mcp.list_tools()}

        names = await tool_visibility.visible_tool_names(all_names)
        self.assertNotIn("create_sales_order", names)
        self.assertNotIn("create_sales_order_line", names)

        await self._grant_add_role()
        await self._disable_read_only()

        names = await tool_visibility.visible_tool_names(all_names)
        self.assertIn("create_sales_order", names)
        self.assertIn("create_sales_order_line", names)
