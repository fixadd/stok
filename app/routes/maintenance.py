from flask import jsonify, render_template, request

from ..services import maintenance_service, repair_service
from ..services.authz import current_actor_name, get_active_user, has_system_role


def register_maintenance_routes(app, deps):
    service_deps = {"current_actor_name": current_actor_name}

    @app.route("/bakim")
    def maintenance_tracking():
        payload = maintenance_service.load_payload(service_deps)
        payload.update(repair_service.load_payload())
        return render_template(
            "maintenance_tracking.html",
            active_page="maintenance_tracking",
            **payload,
        )

    @app.post("/api/inventory/<int:item_id>/maintenance")
    def create_inventory_maintenance(item_id: int):
        if not has_system_role(get_active_user(), "admin"):
            return jsonify({"error": "Bakım kaydı eklemek için admin yetkisi gerekir."}), 403
        payload, status_code = maintenance_service.create(service_deps, item_id, request.get_json(silent=True) or {})
        return jsonify(payload), status_code

    @app.get("/api/inventory/<int:item_id>/maintenance")
    def get_inventory_maintenance(item_id: int):
        payload, status_code = maintenance_service.list_records(service_deps, item_id)
        return jsonify(payload), status_code

    @app.put("/api/inventory/<int:item_id>/maintenance/<int:maintenance_id>")
    def update_inventory_maintenance(item_id: int, maintenance_id: int):
        if not has_system_role(get_active_user(), "admin"):
            return jsonify({"error": "Bakım kaydını düzenlemek için admin yetkisi gerekir."}), 403
        payload, status_code = maintenance_service.update(service_deps, item_id, maintenance_id, request.get_json(silent=True) or {})
        return jsonify(payload), status_code

    @app.delete("/api/inventory/<int:item_id>/maintenance/<int:maintenance_id>")
    def delete_inventory_maintenance(item_id: int, maintenance_id: int):
        if not has_system_role(get_active_user(), "admin"):
            return jsonify({"error": "Bakım kaydını silmek için admin yetkisi gerekir."}), 403
        payload, status_code = maintenance_service.delete(service_deps, item_id, maintenance_id)
        return jsonify(payload), status_code

    @app.get("/api/inventory/<int:item_id>/repair")
    def get_inventory_repairs(item_id: int):
        payload, status_code = repair_service.list_records(item_id)
        return jsonify(payload), status_code

    @app.post("/api/inventory/<int:item_id>/repair")
    def create_inventory_repair(item_id: int):
        if not has_system_role(get_active_user(), "admin"):
            return jsonify({"error": "Tamir kaydı eklemek için admin yetkisi gerekir."}), 403
        payload, status_code = repair_service.create(
            item_id,
            request.get_json(silent=True) or {},
            current_actor_name(),
        )
        return jsonify(payload), status_code

    @app.put("/api/inventory/<int:item_id>/repair/<int:repair_id>")
    def update_inventory_repair(item_id: int, repair_id: int):
        if not has_system_role(get_active_user(), "admin"):
            return jsonify({"error": "Tamir kaydını düzenlemek için admin yetkisi gerekir."}), 403
        payload, status_code = repair_service.update(
            item_id,
            repair_id,
            request.get_json(silent=True) or {},
            current_actor_name(),
        )
        return jsonify(payload), status_code

    @app.delete("/api/inventory/<int:item_id>/repair/<int:repair_id>")
    def delete_inventory_repair(item_id: int, repair_id: int):
        if not has_system_role(get_active_user(), "admin"):
            return jsonify({"error": "Tamir kaydını silmek için admin yetkisi gerekir."}), 403
        payload, status_code = repair_service.delete(item_id, repair_id, current_actor_name())
        return jsonify(payload), status_code
