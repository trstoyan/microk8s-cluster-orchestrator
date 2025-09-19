"""MicroK8s Cluster Orchestrator Application."""

from flask import Flask
from .models.database import init_database

def create_app():
    """Application factory for creating Flask app instances."""
    app = Flask(__name__)
    
    # Initialize database
    init_database(app)
    
    # Register blueprints
    from .controllers import api, web
    app.register_blueprint(api.bp, url_prefix='/api')
    app.register_blueprint(web.bp)
    
    return app
