from flask import render_template

from ..services import stock_service


def register_stock_routes(app, deps):
    get_active_user = deps["get_active_user"]
    has_system_role = deps["has_system_role"]

    @app.route("/stok-takip")
    def stock_tracking():
        from .. import STOCK_METADATA_FIELDS, build_stock_support_options
        from .. import serialize_stock_item, serialize_stock_log

        payload = stock_service.load_tracking_payload(
            serialize_item=serialize_stock_item,
            serialize_log=serialize_stock_log,
            metadata_config=STOCK_METADATA_FIELDS,
            support_options=build_stock_support_options(),
        )
        return render_template(
            "stock_tracking.html",
            active_page="stock_tracking",
            can_manage_stock_data=has_system_role(get_active_user(), "admin"),
            **payload,
        )

    @app.route("/hurdalar")
    def scrap_inventory_page():
        from .. import serialize_inventory_item

        payload = stock_service.load_scrap_inventory_payload(
            serialize_item=serialize_inventory_item,
        )
        can_restore = has_system_role(get_active_user(), "superadmin")
        return render_template(
            "scrap_inventory.html",
            active_page="scrap_inventory",
            can_restore_scrap=can_restore,
            **payload,
        )
