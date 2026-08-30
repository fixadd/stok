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

    @app.get("/api/inventory/<int:item_id>/maintenance")
    def get_inventory_maintenance(item_id: int):
        payload, status_code = deps["list_maintenance_records"](
            item_id
        )

        return jsonify(payload), status_code

    @app.put(
        "/api/inventory/<int:item_id>/maintenance/<int:maintenance_id>"
    )
    def update_inventory_maintenance(
        item_id: int,
        maintenance_id: int,
    ):
        payload, status_code = deps["update_maintenance_record"](
            item_id,
            maintenance_id,
            request.get_json(silent=True) or {},
        )

        return jsonify(payload), status_code

    @app.delete(
        "/api/inventory/<int:item_id>/maintenance/<int:maintenance_id>"
    )
    def delete_inventory_maintenance(
        item_id: int,
        maintenance_id: int,
    ):
        payload, status_code = deps["delete_maintenance_record"](
            item_id,
            maintenance_id,
        )

        return jsonify(payload), status_code
