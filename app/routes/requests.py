from flask import render_template

from ..services import request_service


def register_request_routes(app, deps):
    @app.route("/talep-takip")
    def talep_takip():
        from .. import STOCK_METADATA_FIELDS, STOCK_CATEGORY_LABELS, build_stock_support_options
        from .. import serialize_request_order

        payload = request_service.load_tracking_payload(
            serialize_order=serialize_request_order,
            metadata_config=STOCK_METADATA_FIELDS,
            support_options=build_stock_support_options(),
            category_labels=STOCK_CATEGORY_LABELS,
        )
        return render_template(
            "talep_takip.html",
            active_page="talep_takip",
            **payload,
        )
