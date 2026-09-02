from __future__ import annotations

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException


def _api_request() -> bool:
    return request.path.startswith("/api/")


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(400)
    def bad_request(error):
        if _api_request():
            return jsonify({"error": "Geçersiz istek."}), 400
        return render_template("error.html", code=400, title="Geçersiz İstek", message="Gönderilen istek geçerli değil."), 400

    @app.errorhandler(403)
    def forbidden(error):
        if _api_request():
            return jsonify({"error": "Bu işlem için yetkiniz yok."}), 403
        return render_template("error.html", code=403, title="Yetkisiz Erişim", message="Bu sayfaya erişim yetkiniz yok."), 403

    @app.errorhandler(404)
    def not_found(error):
        if _api_request():
            return jsonify({"error": "Kaynak bulunamadı."}), 404
        return render_template("error.html", code=404, title="Sayfa Bulunamadı", message="Aradığınız sayfa bulunamadı."), 404

    @app.errorhandler(409)
    def conflict(error):
        if _api_request():
            return jsonify({"error": "İşlem mevcut durumla çakışıyor."}), 409
        return render_template("error.html", code=409, title="İşlem Çakışması", message="İşlem mevcut kayıtlarla çakışıyor."), 409

    @app.errorhandler(Exception)
    def internal_error(error):
        if isinstance(error, HTTPException):
            return error
        app.logger.exception("Unhandled application error", exc_info=error)
        if _api_request():
            return jsonify({"error": "Beklenmeyen bir sunucu hatası oluştu."}), 500
        return render_template("error.html", code=500, title="Sunucu Hatası", message="Beklenmeyen bir hata oluştu."), 500
