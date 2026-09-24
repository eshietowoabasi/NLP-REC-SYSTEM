"""WSGI entry point for Gunicorn (``gunicorn wsgi:app``) and ``flask --app wsgi``."""

from app import create_app

app = create_app()
