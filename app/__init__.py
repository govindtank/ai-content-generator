from flask import Flask

from app.config import Config
from app.db import init_db, close_db
from app.auth import auth_bp
from app.routes.dashboard import dashboard_bp
from app.routes.text import text_bp
from app.routes.image import image_bp


def create_app(config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if config:
        app.config.update(config)

    app.teardown_appcontext(close_db)

    with app.app_context():
        init_db()

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(text_bp)
    app.register_blueprint(image_bp)

    @app.errorhandler(404)
    def not_found(e):
        return {"error": "Not found"}, 404

    @app.errorhandler(500)
    def server_error(e):
        return {"error": "Internal server error"}, 500

    return app
