"""Database configuration and initialization."""

import os
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Database instance
db = SQLAlchemy()

# Base model class
Base = declarative_base()

# Database configuration
DATABASE_PATH = os.environ.get('DATABASE_PATH', 'cluster_data.db')
DATABASE_URL = f'sqlite:///{DATABASE_PATH}'

def init_database(app=None):
    """Initialize the database with the Flask app."""
    if app:
        app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(app)
        
        with app.app_context():
            db.create_all()
    else:
        # For standalone usage
        engine = create_engine(DATABASE_URL)
        Base.metadata.create_all(engine)
        return sessionmaker(bind=engine)

def get_session():
    """Get a database session for standalone usage."""
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    return Session()
