from flask import render_template


def register_inventory_routes(app, deps):
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
