"""End-to-end tests for registry-backed MCP mutation tools."""

from __future__ import annotations

from typing import ClassVar

from asgiref.sync import sync_to_async
from company.models import Company
from django.contrib.auth import get_user_model
from django.test import override_settings
from InvenTree.unit_test import InvenTreeTestCase
from mcp.server.mcpserver.exceptions import ToolError
from order.models import SalesOrder
from plugin import registry

from . import context
from .tools.mutations import (
    create_resource,
    delete_resource,
    describe_resource,
    invoke_action,
    update_resource,
)


@override_settings(PLUGIN_TESTING_SETUP=True)
class MCPMutationRegistryTest(InvenTreeTestCase):
    """Exercise generic CRUD, discovery and semantic action dispatch."""

    roles: ClassVar[list[str]] = ["sales_order.view"]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.customer = Company.objects.create(
            name="MCP Mutation Customer",
            is_customer=True,
            is_supplier=False,
        )
        cls.no_access_user = get_user_model().objects.create_user(
            username="mcp-mutation-no-access",
            password="mcp-mutation-no-access",
        )

        registry.reload_plugins(full_reload=True, collect=True)
        registry.set_plugin_state("inventree-mcp", True)

    def _as(self, user):
        context.set_current_user(user)
        self.addCleanup(context.set_current_user, None)

    async def _set_writable(self):
        def _set():
            plugin = registry.get_plugin("inventree-mcp")
            plugin.set_setting("MCP_READ_ONLY", False)
            return plugin

        plugin = await sync_to_async(_set)()
        self.addCleanup(plugin.set_setting, "MCP_READ_ONLY", False)

    async def _grant_crud(self):
        for role in ("sales_order.add", "sales_order.change", "sales_order.delete"):
            await sync_to_async(self.assignRole)(role=role, group=self.group)

    async def test_describe_resource_reports_crud_and_actions(self):
        await self._grant_crud()
        await self._set_writable()
        self._as(self.user)

        info = await describe_resource("sales_order")

        self.assertTrue(info["operations"]["create"]["allowed"])
        self.assertTrue(info["operations"]["update"]["allowed"])
        self.assertTrue(info["operations"]["delete"]["allowed"])
        self.assertIn("reference", info["operations"]["create"]["input_schema"]["properties"])
        self.assertIn("customer", info["operations"]["create"]["input_schema"]["properties"])
        self.assertIn("sales_order.issue", info["actions"])
        self.assertIn("sales_order.allocate", info["actions"])

    async def test_generic_create_update_delete_round_trip(self):
        await self._grant_crud()
        await self._set_writable()
        self._as(self.user)

        created = await create_resource(
            "sales_order",
            {
                "reference": "SO-MCP-GENERIC-001",
                "customer": self.customer.pk,
                "description": "Created generically",
            },
        )
        order_id = created["pk"]

        updated = await update_resource(
            "sales_order",
            order_id,
            {"description": "Updated generically"},
        )
        self.assertEqual(updated["description"], "Updated generically")

        await delete_resource("sales_order", order_id)

        exists = await sync_to_async(
            SalesOrder.objects.filter(pk=order_id).exists
        )()
        self.assertFalse(exists)

    async def test_generic_mutation_still_enforces_inventree_permissions(self):
        await self._set_writable()
        self._as(self.no_access_user)

        with self.assertRaises(ToolError):
            await create_resource(
                "sales_order",
                {
                    "reference": "SO-MCP-GENERIC-002",
                    "customer": self.customer.pk,
                },
            )

    async def test_semantic_action_dispatch_uses_real_action_view(self):
        await sync_to_async(self.assignRole)(
            role="sales_order.add",
            group=self.group,
        )
        await self._set_writable()
        self._as(self.user)

        created = await create_resource(
            "sales_order",
            {
                "reference": "SO-MCP-ACTION-001",
                "customer": self.customer.pk,
            },
        )

        await invoke_action("sales_order.issue", created["pk"], {})

        order = await sync_to_async(SalesOrder.objects.get)(pk=created["pk"])
        self.assertNotEqual(order.status, 10)

    async def test_unknown_resource_and_action_fail_closed(self):
        self._as(self.user)

        with self.assertRaises(ToolError):
            await describe_resource("not_a_real_resource")

        with self.assertRaises(ToolError):
            await invoke_action("not.a.real.action", 1, {})
