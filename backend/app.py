import os

from flask import Flask, jsonify, send_from_directory

from auth.routes import bp as auth_bp
from db import init_db
from errors import register_error_handlers
from locator.routes import bp as locator_bp
from tracker.routes import bp as tracker_bp

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")


def create_app():
    app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")

    register_error_handlers(app)
    app.register_blueprint(auth_bp)
    app.register_blueprint(locator_bp)
    app.register_blueprint(tracker_bp)

    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
        return response

    @app.get("/healthz")
    def healthz():
        return jsonify({"status": "ok"}), 200

    @app.route("/", defaults={"path": "index.html"})
    @app.route("/<path:path>")
    def serve_frontend(path):
        # This is a multi-page site, not an SPA, so this isn't a client-router
        # catch-all. It just means a typoed URL lands on the homepage instead
        # of a bare 404.
        full_path = os.path.join(FRONTEND_DIR, path)
        if not os.path.isfile(full_path):
            return send_from_directory(FRONTEND_DIR, "index.html")
        return send_from_directory(FRONTEND_DIR, path)

    try:
        init_db()
    except Exception as exc:
        # Don't crash the whole app if the DB is briefly unreachable at boot
        # (e.g. gunicorn worker starting before the DB is warm); it'll retry
        # per-request once a real connection is needed.
        app.logger.warning("DB init skipped/failed at startup: %s", exc)

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), debug=True)
