"""Allowlisted InvenTree mutation capabilities exposed through MCP.

This module is the single source of truth for generic CRUD and semantic
actions. It never accepts arbitrary API paths: every resource/action is
mapped to a concrete InvenTree DRF view class and path template.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .view_resolution import resolve_view, resolve_view_any


ViewLoader = Callable[[], type | None]


@dataclass(frozen=True)
class ResourceSpec:
    name: str
    list_loader: ViewLoader
    detail_loader: ViewLoader | None
    list_path: str
    detail_path: str | None
    create: bool = True
    update: bool = True
    delete: bool = True


@dataclass(frozen=True)
class ActionSpec:
    name: str
    loader: ViewLoader
    path: str
    resource: str
    method: str = "POST"
    id_arg: str | None = "pk"
    viewset_action: str | None = None


def _view(module: str, name: str) -> ViewLoader:
    return lambda: resolve_view(module, name)


def _view_any(module: str, names: list[str]) -> ViewLoader:
    return lambda: resolve_view_any(module, names)


RESOURCES: dict[str, ResourceSpec] = {
    "part": ResourceSpec(
        "part", _view("part.api", "PartList"), _view("part.api", "PartDetail"),
        "/api/part/", "/api/part/{id}/",
    ),
    "category": ResourceSpec(
        "category", _view("part.api", "CategoryList"), _view("part.api", "CategoryDetail"),
        "/api/part/category/", "/api/part/category/{id}/",
    ),
    "stock": ResourceSpec(
        "stock", _view("stock.api", "StockList"), _view("stock.api", "StockDetail"),
        "/api/stock/", "/api/stock/{id}/",
    ),
    "location": ResourceSpec(
        "location", _view("stock.api", "StockLocationList"), _view("stock.api", "StockLocationDetail"),
        "/api/stock/location/", "/api/stock/location/{id}/",
    ),
    "stock_location_type": ResourceSpec(
        "stock_location_type", _view("stock.api", "StockLocationTypeList"), _view("stock.api", "StockLocationTypeDetail"),
        "/api/stock/location-type/", "/api/stock/location-type/{id}/",
    ),
    "purchase_order": ResourceSpec(
        "purchase_order",
        _view_any("order.api", ["PurchaseOrderViewSet", "PurchaseOrderList"]),
        _view_any("order.api", ["PurchaseOrderViewSet", "PurchaseOrderDetail"]),
        "/api/order/po/", "/api/order/po/{id}/",
    ),
    "purchase_order_line": ResourceSpec(
        "purchase_order_line",
        _view_any("order.api", ["PurchaseOrderLineItemViewSet", "PurchaseOrderLineItemList"]),
        _view_any("order.api", ["PurchaseOrderLineItemViewSet", "PurchaseOrderLineItemDetail"]),
        "/api/order/po-line/", "/api/order/po-line/{id}/",
    ),
    "sales_order": ResourceSpec(
        "sales_order", _view("order.api", "SalesOrderList"), _view("order.api", "SalesOrderDetail"),
        "/api/order/so/", "/api/order/so/{id}/",
    ),
    "sales_order_line": ResourceSpec(
        "sales_order_line", _view("order.api", "SalesOrderLineItemList"), _view("order.api", "SalesOrderLineItemDetail"),
        "/api/order/so-line/", "/api/order/so-line/{id}/",
    ),
    "sales_order_allocation": ResourceSpec(
        "sales_order_allocation", _view("order.api", "SalesOrderAllocationList"), _view("order.api", "SalesOrderAllocationDetail"),
        "/api/order/so-allocation/", "/api/order/so-allocation/{id}/",
        create=False,
    ),
    "sales_order_shipment": ResourceSpec(
        "sales_order_shipment", _view("order.api", "SalesOrderShipmentList"), _view("order.api", "SalesOrderShipmentDetail"),
        "/api/order/so-shipment/", "/api/order/so-shipment/{id}/",
    ),
    "return_order": ResourceSpec(
        "return_order", _view("order.api", "ReturnOrderList"), _view("order.api", "ReturnOrderDetail"),
        "/api/order/return-order/", "/api/order/return-order/{id}/",
    ),
    "return_order_line": ResourceSpec(
        "return_order_line", _view("order.api", "ReturnOrderLineItemList"), _view("order.api", "ReturnOrderLineItemDetail"),
        "/api/order/return-order-line/", "/api/order/return-order-line/{id}/",
    ),
    "transfer_order": ResourceSpec(
        "transfer_order", _view("order.api", "TransferOrderList"), _view("order.api", "TransferOrderDetail"),
        "/api/order/transfer-order/", "/api/order/transfer-order/{id}/",
    ),
    "transfer_order_line": ResourceSpec(
        "transfer_order_line", _view("order.api", "TransferOrderLineItemList"), _view("order.api", "TransferOrderLineItemDetail"),
        "/api/order/transfer-order-line/", "/api/order/transfer-order-line/{id}/",
    ),
    "transfer_order_allocation": ResourceSpec(
        "transfer_order_allocation", _view("order.api", "TransferOrderAllocationList"), _view("order.api", "TransferOrderAllocationDetail"),
        "/api/order/transfer-order-allocation/", "/api/order/transfer-order-allocation/{id}/",
        create=False,
    ),
    "build_order": ResourceSpec(
        "build_order", _view("build.api", "BuildList"), _view("build.api", "BuildDetail"),
        "/api/build/", "/api/build/{id}/",
    ),
    "build_line": ResourceSpec(
        "build_line", _view("build.api", "BuildLineList"), _view("build.api", "BuildLineDetail"),
        "/api/build/line/", "/api/build/line/{id}/",
    ),
    "build_item": ResourceSpec(
        "build_item", _view("build.api", "BuildItemList"), _view("build.api", "BuildItemDetail"),
        "/api/build/item/", "/api/build/item/{id}/",
        create=False,
    ),
    "company": ResourceSpec(
        "company", _view("company.api", "CompanyList"), _view("company.api", "CompanyDetail"),
        "/api/company/", "/api/company/{id}/",
    ),
    "contact": ResourceSpec(
        "contact", _view("company.api", "ContactList"), _view("company.api", "ContactDetail"),
        "/api/company/contact/", "/api/company/contact/{id}/",
    ),
    "address": ResourceSpec(
        "address", _view("company.api", "AddressList"), _view("company.api", "AddressDetail"),
        "/api/company/address/", "/api/company/address/{id}/",
    ),
    "manufacturer_part": ResourceSpec(
        "manufacturer_part", _view("company.api", "ManufacturerPartList"), _view("company.api", "ManufacturerPartDetail"),
        "/api/company/part/manufacturer/", "/api/company/part/manufacturer/{id}/",
    ),
    "supplier_part": ResourceSpec(
        "supplier_part", _view("company.api", "SupplierPartList"), _view("company.api", "SupplierPartDetail"),
        "/api/company/part/supplier/", "/api/company/part/supplier/{id}/",
    ),
    "supplier_price_break": ResourceSpec(
        "supplier_price_break", _view("company.api", "SupplierPriceBreakList"), _view("company.api", "SupplierPriceBreakDetail"),
        "/api/company/price-break/", "/api/company/price-break/{id}/",
    ),
    "bom_item": ResourceSpec(
        "bom_item", _view("part.api", "BomList"), _view("part.api", "BomDetail"),
        "/api/bom/", "/api/bom/{id}/",
    ),
    "bom_substitute": ResourceSpec(
        "bom_substitute", _view("part.api", "BomItemSubstituteList"), _view("part.api", "BomItemSubstituteDetail"),
        "/api/bom/substitute/", "/api/bom/substitute/{id}/",
    ),
    "part_test_template": ResourceSpec(
        "part_test_template", _view("part.api", "PartTestTemplateList"), _view("part.api", "PartTestTemplateDetail"),
        "/api/part/test-template/", "/api/part/test-template/{id}/",
    ),
    "related_part": ResourceSpec(
        "related_part", _view("part.api", "PartRelatedList"), _view("part.api", "PartRelatedDetail"),
        "/api/part/related/", "/api/part/related/{id}/",
    ),
    "attachment": ResourceSpec(
        "attachment", _view("common.api", "AttachmentList"), _view("common.api", "AttachmentDetail"),
        "/api/attachment/", "/api/attachment/{id}/",
    ),
    "note": ResourceSpec(
        "note", _view("common.api", "NoteList"), _view("common.api", "NoteDetail"),
        "/api/notes/", "/api/notes/{id}/",
    ),
    "parameter": ResourceSpec(
        "parameter", _view("common.api", "ParameterList"), _view("common.api", "ParameterDetail"),
        "/api/parameter/", "/api/parameter/{id}/",
    ),
    "parameter_template": ResourceSpec(
        "parameter_template", _view("common.api", "ParameterTemplateList"), _view("common.api", "ParameterTemplateDetail"),
        "/api/parameter/template/", "/api/parameter/template/{id}/",
    ),
    "project_code": ResourceSpec(
        "project_code", _view("common.api", "ProjectCodeList"), _view("common.api", "ProjectCodeDetail"),
        "/api/project-code/", "/api/project-code/{id}/",
    ),
    "tag": ResourceSpec(
        "tag", _view("common.api", "TagList"), _view("common.api", "TagDetail"),
        "/api/tag/", "/api/tag/{id}/",
    ),
    "selection_list": ResourceSpec(
        "selection_list", _view("common.api", "SelectionListList"), _view("common.api", "SelectionListDetail"),
        "/api/selection-list/", "/api/selection-list/{id}/",
    ),
    "selection_entry": ResourceSpec(
        "selection_entry", _view("common.api", "SelectionEntryList"), _view("common.api", "SelectionEntryDetail"),
        "/api/selection-list/entry/", "/api/selection-list/entry/{id}/",
    ),
    "stock_test_result": ResourceSpec(
        "stock_test_result", _view("stock.api", "StockItemTestResultList"), _view("stock.api", "StockItemTestResultDetail"),
        "/api/stock/test/", "/api/stock/test/{id}/",
    ),
}


ACTIONS: dict[str, ActionSpec] = {
    # Sales orders
    "sales_order.issue": ActionSpec("sales_order.issue", _view("order.api", "SalesOrderIssue"), "/api/order/so/{id}/issue/", "sales_order"),
    "sales_order.hold": ActionSpec("sales_order.hold", _view("order.api", "SalesOrderHold"), "/api/order/so/{id}/hold/", "sales_order"),
    "sales_order.cancel": ActionSpec("sales_order.cancel", _view("order.api", "SalesOrderCancel"), "/api/order/so/{id}/cancel/", "sales_order"),
    "sales_order.complete": ActionSpec("sales_order.complete", _view("order.api", "SalesOrderComplete"), "/api/order/so/{id}/complete/", "sales_order"),
    "sales_order.allocate": ActionSpec("sales_order.allocate", _view("order.api", "SalesOrderAllocate"), "/api/order/so/{id}/allocate/", "sales_order"),
    "sales_order.allocate_serials": ActionSpec("sales_order.allocate_serials", _view("order.api", "SalesOrderAllocateSerials"), "/api/order/so/{id}/allocate-serials/", "sales_order"),
    "sales_order.auto_allocate": ActionSpec("sales_order.auto_allocate", _view("order.api", "SalesOrderAutoAllocate"), "/api/order/so/{id}/auto-allocate/", "sales_order"),
    "sales_order.shipment.ship": ActionSpec("sales_order.shipment.ship", _view("order.api", "SalesOrderShipmentComplete"), "/api/order/so-shipment/{id}/ship/", "sales_order_shipment"),
    # Purchase order custom ViewSet actions (current InvenTree master)
    "purchase_order.issue": ActionSpec("purchase_order.issue", _view_any("order.api", ["PurchaseOrderViewSet", "PurchaseOrderIssue"]), "/api/order/po/{id}/issue/", "purchase_order", viewset_action="issue"),
    "purchase_order.hold": ActionSpec("purchase_order.hold", _view_any("order.api", ["PurchaseOrderViewSet", "PurchaseOrderHold"]), "/api/order/po/{id}/hold/", "purchase_order", viewset_action="hold"),
    "purchase_order.cancel": ActionSpec("purchase_order.cancel", _view_any("order.api", ["PurchaseOrderViewSet", "PurchaseOrderCancel"]), "/api/order/po/{id}/cancel/", "purchase_order", viewset_action="cancel"),
    "purchase_order.complete": ActionSpec("purchase_order.complete", _view_any("order.api", ["PurchaseOrderViewSet", "PurchaseOrderComplete"]), "/api/order/po/{id}/complete/", "purchase_order", viewset_action="complete"),
    "purchase_order.receive": ActionSpec("purchase_order.receive", _view_any("order.api", ["PurchaseOrderViewSet", "PurchaseOrderReceive"]), "/api/order/po/{id}/receive/", "purchase_order", viewset_action="receive"),
    # Return orders
    "return_order.issue": ActionSpec("return_order.issue", _view("order.api", "ReturnOrderIssue"), "/api/order/return-order/{id}/issue/", "return_order"),
    "return_order.hold": ActionSpec("return_order.hold", _view("order.api", "ReturnOrderHold"), "/api/order/return-order/{id}/hold/", "return_order"),
    "return_order.cancel": ActionSpec("return_order.cancel", _view("order.api", "ReturnOrderCancel"), "/api/order/return-order/{id}/cancel/", "return_order"),
    "return_order.complete": ActionSpec("return_order.complete", _view("order.api", "ReturnOrderComplete"), "/api/order/return-order/{id}/complete/", "return_order"),
    "return_order.receive": ActionSpec("return_order.receive", _view("order.api", "ReturnOrderReceive"), "/api/order/return-order/{id}/receive/", "return_order"),
    # Transfer orders
    "transfer_order.issue": ActionSpec("transfer_order.issue", _view("order.api", "TransferOrderIssue"), "/api/order/transfer-order/{id}/issue/", "transfer_order"),
    "transfer_order.hold": ActionSpec("transfer_order.hold", _view("order.api", "TransferOrderHold"), "/api/order/transfer-order/{id}/hold/", "transfer_order"),
    "transfer_order.cancel": ActionSpec("transfer_order.cancel", _view("order.api", "TransferOrderCancel"), "/api/order/transfer-order/{id}/cancel/", "transfer_order"),
    "transfer_order.complete": ActionSpec("transfer_order.complete", _view("order.api", "TransferOrderComplete"), "/api/order/transfer-order/{id}/complete/", "transfer_order"),
    "transfer_order.allocate": ActionSpec("transfer_order.allocate", _view("order.api", "TransferOrderAllocate"), "/api/order/transfer-order/{id}/allocate/", "transfer_order"),
    "transfer_order.allocate_serials": ActionSpec("transfer_order.allocate_serials", _view("order.api", "TransferOrderAllocateSerials"), "/api/order/transfer-order/{id}/allocate-serials/", "transfer_order"),
    # Builds
    "build.issue": ActionSpec("build.issue", _view("build.api", "BuildIssue"), "/api/build/{id}/issue/", "build_order"),
    "build.hold": ActionSpec("build.hold", _view("build.api", "BuildHold"), "/api/build/{id}/hold/", "build_order"),
    "build.cancel": ActionSpec("build.cancel", _view("build.api", "BuildCancel"), "/api/build/{id}/cancel/", "build_order"),
    "build.finish": ActionSpec("build.finish", _view("build.api", "BuildFinish"), "/api/build/{id}/finish/", "build_order"),
    "build.allocate": ActionSpec("build.allocate", _view("build.api", "BuildAllocate"), "/api/build/{id}/allocate/", "build_order"),
    "build.auto_allocate": ActionSpec("build.auto_allocate", _view("build.api", "BuildAutoAllocate"), "/api/build/{id}/auto-allocate/", "build_order"),
    "build.unallocate": ActionSpec("build.unallocate", _view("build.api", "BuildUnallocate"), "/api/build/{id}/unallocate/", "build_order"),
    "build.consume": ActionSpec("build.consume", _view("build.api", "BuildConsume"), "/api/build/{id}/consume/", "build_order"),
    "build.output.create": ActionSpec("build.output.create", _view("build.api", "BuildOutputCreate"), "/api/build/{id}/output/", "build_order"),
    "build.output.complete": ActionSpec("build.output.complete", _view("build.api", "BuildOutputComplete"), "/api/build/{id}/output/complete/", "build_order"),
    "build.output.scrap": ActionSpec("build.output.scrap", _view("build.api", "BuildOutputScrap"), "/api/build/{id}/output/scrap/", "build_order"),
    "build.output.delete": ActionSpec("build.output.delete", _view("build.api", "BuildOutputDelete"), "/api/build/{id}/output/delete/", "build_order"),
    # Stock workflow
    "stock.add": ActionSpec("stock.add", _view("stock.api", "StockAdd"), "/api/stock/add/", "stock", id_arg=None),
    "stock.remove": ActionSpec("stock.remove", _view("stock.api", "StockRemove"), "/api/stock/remove/", "stock", id_arg=None),
    "stock.count": ActionSpec("stock.count", _view("stock.api", "StockCount"), "/api/stock/count/", "stock", id_arg=None),
    "stock.transfer": ActionSpec("stock.transfer", _view("stock.api", "StockTransfer"), "/api/stock/transfer/", "stock", id_arg=None),
    "stock.return": ActionSpec("stock.return", _view("stock.api", "StockReturn"), "/api/stock/return/", "stock", id_arg=None),
    "stock.change_status": ActionSpec("stock.change_status", _view("stock.api", "StockChangeStatus"), "/api/stock/status/", "stock", id_arg=None),
    "stock.assign": ActionSpec("stock.assign", _view("stock.api", "StockAssign"), "/api/stock/assign/", "stock", id_arg=None),
    "stock.merge": ActionSpec("stock.merge", _view("stock.api", "StockMerge"), "/api/stock/merge/", "stock", id_arg=None),
    "stock.serialize": ActionSpec("stock.serialize", _view("stock.api", "StockItemSerialize"), "/api/stock/{id}/serialize/", "stock"),
    "stock.install": ActionSpec("stock.install", _view("stock.api", "StockItemInstall"), "/api/stock/{id}/install/", "stock"),
    "stock.uninstall": ActionSpec("stock.uninstall", _view("stock.api", "StockItemUninstall"), "/api/stock/{id}/uninstall/", "stock"),
    "stock.convert": ActionSpec("stock.convert", _view("stock.api", "StockItemConvert"), "/api/stock/{id}/convert/", "stock"),
    "stock.disassemble": ActionSpec("stock.disassemble", _view("stock.api", "StockItemDisassemble"), "/api/stock/{id}/disassemble/", "stock"),
    # Part / BOM workflow
    "part.copy_bom": ActionSpec("part.copy_bom", _view("part.api", "PartCopyBOM"), "/api/part/{id}/bom/copy/", "part"),
    "part.validate_bom": ActionSpec("part.validate_bom", _view("part.api", "PartValidateBOM"), "/api/part/{id}/bom/validate/", "part", method="PATCH"),
    "bom_item.validate": ActionSpec("bom_item.validate", _view("part.api", "BomItemValidate"), "/api/bom/{id}/validate/", "bom_item", method="PATCH"),
}
