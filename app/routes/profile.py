from flask import flash, redirect, render_template, request, url_for

from ..queries.user_queries import get_user, list_active_users
from ..services.validation import validate_password


def register_profile_routes(app, deps):
    @app.route("/profil")
    def profile():
        profile_user = deps["get_active_user"]()
        can_switch_users = deps["has_system_role"](profile_user, "superadmin")
        users = list_active_users(limit=500) if can_switch_users else ([profile_user] if profile_user else [])

        return render_template(
            "profile.html",
            active_page="profile",
            users=users,
            profile_user=profile_user,
            can_switch_users=can_switch_users,
        )

    @app.post("/profil/kullanici")
    def profile_switch_user():
        active_user = deps["get_active_user"]()
        if not deps["has_system_role"](active_user, "superadmin"):
            flash("Bu işlemi gerçekleştirmek için yetkiniz yok.", "danger")
            return redirect(url_for("profile"))

        user_id = deps["parse_int_or_none"](request.form.get("user_id"))
        user = get_user(user_id) if user_id is not None else None
        if user is None:
            flash("Lütfen geçerli bir kullanıcı seçin.", "danger")
            return redirect(url_for("profile"))

        deps["set_active_user"](user)
        flash(f"{user.first_name} {user.last_name} profili görüntüleniyor.", "success")
        return redirect(url_for("profile"))

    @app.post("/profil/tema")
    def profile_update_theme():
        user = deps["get_active_user"]()
        if user is None:
            flash("Tema güncellemek için kayıtlı kullanıcı bulunamadı.", "danger")
            return redirect(url_for("profile"))

        theme = (request.form.get("theme") or "").strip()
        if theme not in deps["THEME_OPTIONS"]:
            flash("Lütfen geçerli bir tema seçin.", "warning")
            return redirect(url_for("profile"))

        user.preferred_theme = theme
        deps["record_activity"](
            area="profil",
            action="Tema güncellendi",
            description=f"{user.first_name} {user.last_name}",
            actor=deps["current_actor_name"](),
            metadata={"user_id": user.id, "theme": theme},
        )
        deps["db"].session.commit()
        flash("Tema tercihi güncellendi.", "success")
        return redirect(url_for("profile"))

    @app.post("/profil/sifre")
    def profile_update_password():
        user = deps["get_active_user"]()
        if user is None:
            flash("Şifre güncellemek için kullanıcı bulunamadı.", "danger")
            return redirect(url_for("profile"))

        new_password = request.form.get("new_password") or ""
        confirm_password = request.form.get("confirm_password") or ""
        if not new_password or not confirm_password:
            flash("Lütfen yeni şifre alanlarını doldurun.", "warning")
            return redirect(url_for("profile"))
        if new_password != confirm_password:
            flash("Yeni şifre ve doğrulama şifresi eşleşmiyor.", "danger")
            return redirect(url_for("profile"))

        _, password_error = validate_password(new_password, username=user.username or "")
        if password_error:
            flash(password_error, "warning")
            return redirect(url_for("profile"))

        user.password_hash = deps["generate_password_hash"](new_password)
        user.must_change_password = False
        deps["record_activity"](
            area="profil",
            action="Şifre güncellendi",
            description=f"{user.first_name} {user.last_name}",
            actor=deps["current_actor_name"](),
            metadata={"user_id": user.id},
        )
        deps["db"].session.commit()
        flash("Şifre başarıyla güncellendi.", "success")
        return redirect(url_for("profile"))
