from flask import render_template

from ..services import inventory_service, license_tracking_service


def register_inventory_routes(app, deps):
    @app.route("/envanter-takip")
    def inventory_tracking():
        from .. import serialize_inventory_item

        payload = inventory_service.load_tracking_payload(
            serialize_item=serialize_inventory_item,
        )
        return render_template(
            "inventory_tracking.html",
            active_page="inventory_tracking",
            **payload,
        )

    @app.route("/lisans-takip")
    def license_tracking():
        from .. import serialize_inventory_item, serialize_license_record

        payload = license_tracking_service.load_tracking_payload(
            serialize_license=serialize_license_record,
            serialize_item=serialize_inventory_item,
        )
        return render_template(
            "license_tracking.html",
            active_page="license_tracking",
            **payload,
        )
