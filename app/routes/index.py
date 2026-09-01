from flask import render_template

from .license_history import register_license_history_routes
from .license_stock import register_license_stock_routes
from .stock_api import register_stock_api_routes


def register_index_routes(app, deps):
    register_license_history_routes(app, deps)
    register_license_stock_routes(app, deps)
    register_stock_api_routes(app)

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
