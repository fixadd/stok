from flask import jsonify, render_template, request


def register_maintenance_routes(app, deps):
    @app.route("/bakim")
    def maintenance_tracking():
        payload = deps["load_maintenance_payload"]()
        return render_template(
            "maintenance_tracking.html",
            active_page="maintenance_tracking",
            **payload,
        )

    @app.post("/api/inventory/<int:item_id>/maintenance")
    def create_inventory_maintenance(item_id: int):
        payload, status_code = deps["create_maintenance_record"](
            item_id,
            request.get_json(silent=True) or {},
        )
        return jsonify(payload), status_code
