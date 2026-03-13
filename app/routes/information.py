from flask import render_template


def register_information_routes(app, deps):
    @app.route("/bilgiler")
    def information_list():
        payload = deps["load_information_payload"]()
        return render_template(
            "information/list.html",
            active_page="information",
            **payload,
        )
