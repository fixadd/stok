from flask import render_template


def register_index_routes(app, deps=None):
    def load_recent_activity():
        from app import load_recent_activity as loader
        return loader()

    def load_dashboard_metrics():
        from app import load_dashboard_metrics as loader
        return loader()

    @app.route("/")
    def index():
        return render_template(
            "index.html",
            active_page="index",
            recent_activity=load_recent_activity(),
            dashboard=load_dashboard_metrics(),
        )
