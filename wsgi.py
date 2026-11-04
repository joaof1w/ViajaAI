"""Entrada WSGI para produção (gunicorn, PythonAnywhere, Render...).

    gunicorn wsgi:app
"""
from backend.app import create_app

app = create_app()
