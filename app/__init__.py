from flask import Flask

from app.config import Config
from app.db import init_db, close_db
from app.auth import auth_bp
from app.routes.dashboard import dashboard_bp
from app.routes.text import text_bp
from app.routes.image import image_bp
from app.routes.providers import provider_bp
from app.routes.prompts import prompts_bp
from app.routes.formats import formats_bp
from app.routes.batch import batch_bp
from app.routes.export import export_bp
from app.routes.folders import folders_bp
from app.routes.workbench import workbench_bp
from app.routes.seo import seo_bp
from app.routes.calendar import calendar_bp
from app.routes.campaigns import campaigns_bp
from app.routes.analytics import analytics_bp
from app.routes.integrations import integrations_bp
from app.routes.comments import comments_bp
from app.routes.agent import agent_bp
from app.providers import router
from app.providers.gemini import GeminiProvider
from app.providers.openai import OpenAIProvider
from app.providers.anthropic import AnthropicProvider


def create_app(config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if config:
        app.config.update(config)

    app.teardown_appcontext(close_db)

    with app.app_context():
        init_db()

    # Register provider backends
    router.register(GeminiProvider)
    router.register(OpenAIProvider)
    router.register(AnthropicProvider)

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(text_bp)
    app.register_blueprint(image_bp)
    app.register_blueprint(provider_bp)
    app.register_blueprint(prompts_bp)
    app.register_blueprint(formats_bp)
    app.register_blueprint(batch_bp)
    app.register_blueprint(export_bp)
    app.register_blueprint(folders_bp)
    app.register_blueprint(workbench_bp)
    app.register_blueprint(seo_bp)
    app.register_blueprint(calendar_bp)
    app.register_blueprint(campaigns_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(integrations_bp)
    app.register_blueprint(comments_bp)
    app.register_blueprint(agent_bp)

    @app.errorhandler(404)
    def not_found(e):
        return {"error": "Not found"}, 404

    @app.errorhandler(500)
    def server_error(e):
        return {"error": "Internal server error"}, 500

    @app.context_processor
    def inject_globals():
        return {
            "app_name": "ContentForge",
            "app_logo": "⚒️",
            "app_tagline": "Forge your ideas into content that works",
        }

    return app
