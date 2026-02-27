from flask import flash, redirect, render_template, url_for


def register_admin_routes(app, deps):
    get_active_user = deps["get_active_user"]
    has_system_role = deps["has_system_role"]
    load_admin_panel_payload = deps["load_admin_panel_payload"]

    @app.route("/admin-panel")
    def admin_panel():
        user = get_active_user()
        if not has_system_role(user, "admin"):
            flash("Admin paneline erişmek için yetkiniz yok.", "danger")
            return redirect(url_for("index"))
        admin_payload = load_admin_panel_payload()
        return render_template(
            "admin_panel.html",
            active_page="admin_panel",
            can_manage_users=has_system_role(user, "superadmin"),
            can_manage_data=has_system_role(user, "admin"),
            system_role_choices=[
                {"value": key, "label": deps["SYSTEM_ROLE_LABELS"][key]}
                for key in ("user", "admin")
            ],
            **admin_payload,
        )
