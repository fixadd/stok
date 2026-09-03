from __future__ import annotations

from flask import flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from ..queries.user_queries import get_by_username
from ..services.security import record_login_attempt
from ..services.validation import validate_password
from .index import register_index_routes


def register_auth_routes(app, deps):
    register_index_routes(app)

    get_active_user = deps["get_active_user"]
    is_safe_redirect_target = deps["is_safe_redirect_target"]
    set_active_user = deps["set_active_user"]
    record_activity = deps["record_activity"]
    current_actor_name = deps["current_actor_name"]
    db = deps["db"]

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
            password = request.form.get("password") or ""
            next_param = request.form.get("next") or next_param
            user = get_by_username(username)

            if user and user.password_hash and check_password_hash(user.password_hash, password):
                record_login_attempt(True)
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

            record_login_attempt(False)
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
            new_password = request.form.get("new_password") or ""
            confirm_password = request.form.get("confirm_password") or ""
            form_target = request.form.get("next")
            if form_target and is_safe_redirect_target(form_target):
                session["post_password_change_redirect"] = form_target
                target = form_target

            if not new_password or not confirm_password:
                error = "Lütfen yeni şifrenizi iki alana da yazın."
            elif new_password != confirm_password:
                error = "Yeni şifre ve doğrulama alanı eşleşmiyor."
            else:
                _, password_error = validate_password(new_password, username=user.username or "")
                if password_error:
                    error = password_error
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

    @app.post("/cikis")
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
