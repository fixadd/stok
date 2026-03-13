from flask import render_template


def register_request_routes(app, deps):
    @app.route("/talep-takip")
    def talep_takip():
        payload = deps["load_request_groups"]()
        return render_template(
            "talep_takip.html",
            active_page="talep_takip",
            **payload,
        )
