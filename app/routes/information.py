from __future__ import annotations

from flask import abort, flash, jsonify, redirect, render_template, request, url_for


def register_information_routes(app, deps):
    get_active_user = deps.get("get_active_user")
    has_system_role = deps.get("has_system_role")

    def require_admin_redirect():
        user = get_active_user() if get_active_user else None
        if has_system_role and has_system_role(user, "admin"):
            return None
        flash("Bilgi kayıtlarını değiştirmek için admin yetkisi gerekir.", "danger")
        return redirect(url_for("information_list"))

    @app.route("/bilgiler")
    def information_list():
        payload = deps["load_information_payload"]()
        return render_template(
            "information/list.html",
            active_page="information",
            **payload,
        )

    @app.post("/bilgiler")
    def create_information_entry():
        guard = require_admin_redirect()
        if guard is not None:
            return guard

        title = (request.form.get("title") or "").strip()
        category_id = deps["parse_int_or_none"](request.form.get("category_id"))
        content = (request.form.get("content") or "").strip()

        if not title or not category_id or not content:
            flash("Lütfen başlık, kategori ve içerik alanlarını doldurun.", "danger")
            return redirect(url_for("information_list"))

        category = deps["InfoCategory"].query.get(category_id)
        if category is None:
            flash("Seçilen kategori bulunamadı.", "danger")
            return redirect(url_for("information_list"))

        image_filename = deps["save_information_image"](request.files.get("photo"))

        entry = deps["InfoEntry"](
            title=title,
            category=category,
            content=content,
            image_filename=image_filename,
        )

        attachments = request.files.getlist("attachments")
        for file in attachments:
            saved = deps["save_information_file"](file)
            if not saved:
                continue

            stored_name, original_name = saved
            entry.attachments.append(
                deps["InfoAttachment"](
                    filename=stored_name,
                    original_name=original_name,
                    content_type=file.mimetype,
                )
            )

        deps["db"].session.add(entry)
        deps["db"].session.flush()

        deps["record_activity"](
            area="bilgi",
            action="Bilgi kaydı oluşturuldu",
            description=title,
            metadata={"info_id": entry.id},
        )

        deps["db"].session.commit()

        flash("Bilgi kaydı başarıyla oluşturuldu.", "success")
        return redirect(url_for("information_list"))

    @app.route("/bilgiler/<int:entry_id>")
    def information_detail(entry_id: int):
        entry = deps["load_information_entry"](entry_id)
        if entry is None:
            abort(404)

        categories = (
            deps["InfoCategory"]
            .query
            .order_by(deps["InfoCategory"].name)
            .all()
        )

        return render_template(
            "information/detail.html",
            active_page="information",
            entry=entry,
            categories=categories,
            mode="view",
        )

    @app.route("/bilgiler/<int:entry_id>/duzenle", methods=["GET", "POST"])
    def information_edit(entry_id: int):
        guard = require_admin_redirect()
        if guard is not None:
            return guard

        entry = deps["load_information_entry"](entry_id)
        if entry is None:
            abort(404)

        if request.method == "POST":
            title = (request.form.get("title") or "").strip()
            category_id = deps["parse_int_or_none"](request.form.get("category_id"))
            content = (request.form.get("content") or "").strip()

            if not title or not category_id or not content:
                flash("Lütfen başlık, kategori ve içerik alanlarını doldurun.", "danger")
                return redirect(url_for("information_edit", entry_id=entry.id))

            category = deps["InfoCategory"].query.get(category_id)
            if category is None:
                flash("Seçilen kategori bulunamadı.", "danger")
                return redirect(url_for("information_edit", entry_id=entry.id))

            entry.title = title
            entry.category = category
            entry.content = content

            new_filename = deps["save_information_image"](request.files.get("photo"))
            if new_filename:
                deps["remove_information_image"](entry.image_filename)
                entry.image_filename = new_filename

            remove_ids = {
                deps["parse_int_or_none"](raw)
                for raw in request.form.getlist("remove_attachments")
            }
            remove_ids.discard(None)

            if remove_ids:
                for attachment in list(entry.attachments):
                    if attachment.id in remove_ids:
                        deps["remove_information_file"](attachment.filename)
                        deps["db"].session.delete(attachment)

            for file in request.files.getlist("attachments"):
                saved = deps["save_information_file"](file)
                if not saved:
                    continue

                stored_name, original_name = saved
                entry.attachments.append(
                    deps["InfoAttachment"](
                        filename=stored_name,
                        original_name=original_name,
                        content_type=file.mimetype,
                    )
                )

            deps["record_activity"](
                area="bilgi",
                action="Bilgi kaydı güncellendi",
                description=title,
                metadata={"info_id": entry.id},
            )
            deps["db"].session.commit()

            flash("Bilgi kaydı güncellendi.", "success")
            return redirect(url_for("information_detail", entry_id=entry.id))

        categories = (
            deps["InfoCategory"]
            .query
            .order_by(deps["InfoCategory"].name)
            .all()
        )

        return render_template(
            "information/detail.html",
            active_page="information",
            entry=entry,
            categories=categories,
            mode="edit",
        )
