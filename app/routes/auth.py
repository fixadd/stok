from __future__ import annotations

from flask import flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from ..services.authz import has_system_role


def register_auth_routes(app, deps):
    get_active_user = deps["get_active_user"]
    is_safe_redirect_target = deps["is_safe_redirect_target"]
    active_users_query = deps["active_users_query"]
    User = deps["User"]
    func = deps["func"]
    set_active_user = deps["set_active_user"]
    record_activity = deps["record_activity"]
    current_actor_name = deps["current_actor_name"]
    db = deps["db"]

    @app.before_request
    def enforce_api_write_roles():
        endpoint = request.endpoint or ""
        if endpoint in {"login", "static", "force_password_change", "logout"}:
            return
        if endpoint.startswith("static"):
            return

        user = get_active_user()
        if user is None:
            return

        path = request.path
        method = request.method.upper()
        if method not in {"POST", "PUT", "PATCH", "DELETE"}:
            return

        requires_admin = (
            path.startswith("/api/options/")
            or path.startswith("/api/ldap-profiles")
            or path.startswith("/api/catalog/products")
            or path == "/api/stock"
            or path.startswith("/api/stock/")
            or (path.startswith("/api/inventory/") and path.endswith(("/stock", "/scrap")))
            or (path.startswith("/api/requests/") and path.endswith("/actions"))
        )
        requires_superadmin = path.startswith("/api/inventory/") and path.endswith(
            "/restore-from-scrap"
        )

        if requires_superadmin:
            if not has_system_role(user, "superadmin"):
                return jsonify({"error": "Bu işlem için süper admin yetkisi gerekir."}), 403
            return

        if requires_admin and not has_system_role(user, "admin"):
            return jsonify({"error": "Bu işlem için admin yetkisi gerekir."}), 403

    @app.route("/giris", methods=["GET", "POST"])
    def login():
        if get_active_user():
            next_param = request.args.get("next")
            if next_param and is_safe_redirect_target(next_param):
                return redirect(next_param)
            return redirect(url_for("index"))

        error: str | None = None
        next_param = request.args.get("next")

        if request.method == "POST":
            username = (request.form.get("username") or "").strip()
            password = (request.form.get("password") or "").strip()
            next_param = request.form.get("next") or next_param

            user = (
                active_users_query()
                .filter(func.lower(User.username) == username.lower())
                .first()
                if username
                else None
            )

            if user and user.password_hash and check_password_hash(user.password_hash, password):
                session.clear()
                session.permanent = True
                set_active_user(user)
                record_activity(
                    area="auth",
                    action="Oturum açıldı",
                    actor=current_actor_name(),
                    metadata={"user_id": user.id, "username": user.username},
                )
                db.session.commit()
                target = next_param if is_safe_redirect_target(next_param) else None
                if user.must_change_password:
                    session.pop("post_password_change_redirect", None)
                    if target:
                        session["post_password_change_redirect"] = target
                    return redirect(url_for("force_password_change"))
                session.pop("post_password_change_redirect", None)
                return redirect(target or url_for("index"))

            error = "Kullanıcı adı veya şifre hatalı."

        return render_template(
            "login.html",
            error=error,
            next_target=next_param if is_safe_redirect_target(next_param) else "",
        )

    @app.route("/ilk-giris-sifre", methods=["GET", "POST"])
    def force_password_change():
        user = get_active_user()
        if user is None:
            flash("Lütfen önce oturum açın.", "warning")
            return redirect(url_for("login"))

        if not user.must_change_password:
            target = session.pop("post_password_change_redirect", None)
            if target and is_safe_redirect_target(target):
                return redirect(target)
            target = None
        else:
            query_target = request.args.get("next")
            if query_target and is_safe_redirect_target(query_target):
                session["post_password_change_redirect"] = query_target
                target = query_target
            else:
                target = session.get("post_password_change_redirect")

        error: str | None = None

        if request.method == "POST":
            new_password = (request.form.get("new_password") or "").strip()
            confirm_password = (request.form.get("confirm_password") or "").strip()
            form_target = request.form.get("next")
            if form_target and is_safe_redirect_target(form_target):
                session["post_password_change_redirect"] = form_target
                target = form_target

            if not new_password or not confirm_password:
                error = "Lütfen yeni şifrenizi iki alana da yazın."
            elif new_password != confirm_password:
                error = "Yeni şifre ve doğrulama alanı eşleşmiyor."
            elif len(new_password) < 8:
                error = "Şifre en az 8 karakter olmalıdır."
            elif new_password.lower() == user.username.lower():
                error = "Şifreniz kullanıcı adınızla aynı olamaz."
            else:
                user.password_hash = generate_password_hash(new_password)
                user.must_change_password = False
                record_activity(
                    area="auth",
                    action="İlk giriş şifresi güncellendi",
                    actor=current_actor_name(),
                    metadata={"user_id": user.id, "username": user.username},
                )
                db.session.commit()
                flash("Yeni şifreniz kaydedildi.", "success")
                session.pop("post_password_change_redirect", None)
                if target and is_safe_redirect_target(target):
                    return redirect(target)
                return redirect(url_for("index"))

        return render_template(
            "force_password_change.html",
            error=error,
            next_target=target if target and is_safe_redirect_target(target) else "",
        )

    @app.route("/cikis")
    def logout():
        user = get_active_user()
        session.clear()
        if user:
            record_activity(
                area="auth",
                action="Oturum kapatıldı",
                actor=f"{user.first_name} {user.last_name}".strip() or user.username,
                metadata={"user_id": user.id, "username": user.username},
            )
            db.session.commit()
        flash("Oturum kapatıldı.", "info")
        return redirect(url_for("login"))
