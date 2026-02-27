from flask import render_template


def register_inventory_routes(app, deps):
    @app.route("/")
    def index():
        recent_activity = deps["load_recent_activity"]()
        dashboard = deps["load_dashboard_metrics"]()
        return render_template(
            "index.html",
            active_page="index",
            recent_activity=recent_activity,
            dashboard=dashboard,
        )

    @app.route("/envanter-takip")
    def inventory_tracking():
        payload = deps["load_inventory_payload"]()
        return render_template(
            "inventory_tracking.html",
            active_page="inventory_tracking",
            **payload,
        )

    @app.route("/lisans-takip")
    def license_tracking():
        payload = deps["load_license_payload"]()
        return render_template(
            "license_tracking.html",
            active_page="license_tracking",
            **payload,
        )

    @app.route("/yazici-takip")
    def printer_tracking():
        payload = deps["load_printer_payload"]()
        return render_template(
            "printer_tracking.html",
            active_page="printer_tracking",
            **payload,
        )
