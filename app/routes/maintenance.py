from flask import jsonify, render_template, request

from ..services import maintenance_service


def register_maintenance_routes(app, deps):
    service_deps = {
        "current_actor_name": deps["current_actor_name"],
    }

    @app.route("/bakim")
    def maintenance_tracking():
        payload = maintenance_service.load_payload(service_deps)
        return render_template(
            "maintenance_tracking.html",
            active_page="maintenance_tracking",
            **payload,
        )

    @app.post("/api/inventory/<int:item_id>/maintenance")
    def create_inventory_maintenance(item_id: int):
        if not deps["has_system_role"](deps["get_active_user"](), "admin"):
            return jsonify({"error": "Bakım kaydı eklemek için admin yetkisi gerekir."}), 403
        payload, status_code = maintenance_service.create(
            service_deps,
            item_id,
            request.get_json(silent=True) or {},
        )
        return jsonify(payload), status_code

    @app.get("/api/inventory/<int:item_id>/maintenance")
    def get_inventory_maintenance(item_id: int):
        payload, status_code = maintenance_service.list_records(service_deps, item_id)
        return jsonify(payload), status_code

    @app.put("/api/inventory/<int:item_id>/maintenance/<int:maintenance_id>")
    def update_inventory_maintenance(item_id: int, maintenance_id: int):
        if not deps["has_system_role"](deps["get_active_user"](), "admin"):
            return jsonify({"error": "Bakım kaydını düzenlemek için admin yetkisi gerekir."}), 403
        payload, status_code = maintenance_service.update(
            service_deps,
            item_id,
            maintenance_id,
            request.get_json(silent=True) or {},
        )
        return jsonify(payload), status_code

    @app.delete("/api/inventory/<int:item_id>/maintenance/<int:maintenance_id>")
    def delete_inventory_maintenance(item_id: int, maintenance_id: int):
        if not deps["has_system_role"](deps["get_active_user"](), "admin"):
            return jsonify({"error": "Bakım kaydını silmek için admin yetkisi gerekir."}), 403
        payload, status_code = maintenance_service.delete(
            service_deps,
            item_id,
            maintenance_id,
        )
        return jsonify(payload), status_code
