"""WSGI entrypoint for production runtimes."""

from app import create_app

application = create_app()

