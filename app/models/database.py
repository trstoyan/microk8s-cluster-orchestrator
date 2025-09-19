"""Database configuration and initialization."""

import os
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Database instance for Flask
db = SQLAlchemy()

# Base model class for standalone usage
Base = declarative_base()

# Database configuration
DATABASE_PATH = os.environ.get('DATABASE_PATH', 'cluster_data.db')
DATABASE_URL = f'sqlite:///{DATABASE_PATH}'

def init_database(app=None):
    """Initialize the database with the Flask app."""
    if app:
        # Use absolute path to ensure Flask-SQLAlchemy uses the same database file
        import os
        abs_database_path = os.path.abspath(DATABASE_PATH)
        abs_database_url = f'sqlite:///{abs_database_path}'
        app.config['SQLALCHEMY_DATABASE_URI'] = abs_database_url
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(app)
        
        with app.app_context():
            # Import models to register them with Flask-SQLAlchemy
            from . import node, cluster, operation, configuration, router_switch
            db.create_all()
    else:
        # For standalone usage
        engine = create_engine(DATABASE_URL)
        # Import models to register them with SQLAlchemy Base
        from . import node, cluster, operation, configuration, router_switch
        Base.metadata.create_all(engine)
        return sessionmaker(bind=engine)

def get_session():
    """Get a database session for standalone usage."""
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    return Session()
