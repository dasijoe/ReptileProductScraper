"""
Initializing the Flask application with its configurations and components.
"""
import os
import logging
from datetime import timedelta
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Initialize Flask app
app = Flask(__name__)
app.config.from_pyfile('config.py')

# Set secret key from environment with fallback
app.config['SECRET_KEY'] = os.environ.get('SESSION_SECRET', app.config['SECRET_KEY'])
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)

# Initialize PostgreSQL database
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize database
db = SQLAlchemy(app)

# Ensure data directories exist
os.makedirs('data', exist_ok=True)
os.makedirs('data/exports', exist_ok=True)
os.makedirs('data/images', exist_ok=True)
os.makedirs('data/logs', exist_ok=True)

# Import models to create tables
from app.models.database import init_db
from app.routes import register_routes

# Initialize database tables
with app.app_context():
    init_db()

# Register routes
register_routes(app)
