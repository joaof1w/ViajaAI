"""Extensões compartilhadas (evita import circular entre app, models e services)."""
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
cors = CORS()
