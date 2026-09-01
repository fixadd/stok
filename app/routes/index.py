from flask import render_template

from .license_history import register_license_history_routes


def register_index_routes(app, deps):
    register_license_history_routes(app, deps)

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
