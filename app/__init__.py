"""MicroK8s Cluster Orchestrator Application."""

from flask import Flask
from flask_login import LoginManager
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
    
    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        from .models.flask_models import User
        return User.query.get(int(user_id))
    
    # Register blueprints
    from .controllers import api, web, auth
    app.register_blueprint(auth.bp, url_prefix='/auth')
    app.register_blueprint(api.bp, url_prefix='/api')
    app.register_blueprint(web.bp)
    
    return app
