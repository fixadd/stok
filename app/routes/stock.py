from flask import render_template


def register_stock_routes(app, deps):
    get_active_user = deps["get_active_user"]
    has_system_role = deps["has_system_role"]

    @app.route("/stok-takip")
    def stock_tracking():
        payload = deps["load_stock_payload"]()
        return render_template(
            "stock_tracking.html",
            active_page="stock_tracking",
            can_manage_stock_data=has_system_role(get_active_user(), "admin"),
            **payload,
        )

    @app.route("/hurdalar")
    def scrap_inventory_page():
        payload = deps["load_scrap_inventory_payload"]()
        can_restore = has_system_role(get_active_user(), "superadmin")
        return render_template(
            "scrap_inventory.html",
            active_page="scrap_inventory",
            can_restore_scrap=can_restore,
            **payload,
        )
