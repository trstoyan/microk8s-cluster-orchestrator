"""MicroK8s Cluster Orchestrator Application."""

from flask import Flask
from .models.database import init_database
from .utils.config import config

def create_app():
    """Application factory for creating Flask app instances."""
    app = Flask(__name__)
    
    # Configure Flask settings from config
    app.config['SECRET_KEY'] = config.get('flask.secret_key', 'change-this-in-production')
    app.config['DEBUG'] = config.get('flask.debug', False)
    
    # Initialize database
    init_database(app)
    
    # Register blueprints
    from .controllers import api, web
    app.register_blueprint(api.bp, url_prefix='/api')
    app.register_blueprint(web.bp)
    
    return app
