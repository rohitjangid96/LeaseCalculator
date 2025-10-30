"""
Main Lease Management Application
Production-grade Flask application with proper structure

VBA Source: None (Flask application - new functionality)
"""

from flask import Flask, session
from flask_cors import CORS
import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Import configuration
from config import config, Config

# Import blueprints
from auth import auth_bp
from api import api_bp
from complete_lease_backend import calc_bp
from pdf_upload_backend import pdf_bp
from document_backend import doc_bp

# Import database
import database


def setup_logging(log_dir: Path):
    """Setup application logging"""
    log_dir.mkdir(exist_ok=True)
    
    log_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler with rotation
    log_file = log_dir / 'lease_app.log'
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=Config.LOG_MAX_BYTES, 
        backupCount=Config.LOG_BACKUP_COUNT
    )
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.DEBUG)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    return root_logger


def create_app(config_name=None):
    """Application factory pattern"""
    app = Flask(__name__, 
                template_folder='frontend/templates',
                static_folder='frontend/static')
    
    # Load configuration
    config_name = config_name or os.environ.get('FLASK_ENV', 'default')
    app.config.from_object(config[config_name])
    
    # Setup logging
    logger = setup_logging(Path(app.config['LOG_DIR']))
    logger.info("🚀 Initializing Lease Management Application...")
    
    # Initialize CORS
    CORS(app, 
         resources={r"/api/*": {"origins": app.config['CORS_ORIGINS']}}, 
         supports_credentials=True)
    
    # Initialize database
    database.init_database()
    logger.info("✅ Database initialized")
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(calc_bp)
    app.register_blueprint(pdf_bp)
    app.register_blueprint(doc_bp)
    logger.info("✅ Blueprints registered")
    
    # Session configuration
    @app.before_request
    def make_session_permanent():
        session.permanent = False
    
    # Root routes - serve HTML pages
    @app.route('/')
    def index():
        from flask import render_template, redirect
        return redirect('/login.html')
    
    @app.route('/login')
    @app.route('/login.html')
    def login_page():
        from flask import render_template
        try:
            return render_template('login.html')
        except Exception as e:
            logger.error(f"Error rendering login.html: {e}")
            return f"Error loading login page: {e}", 500
    
    @app.route('/dashboard')
    @app.route('/dashboard.html')
    def dashboard_page():
        from flask import render_template
        try:
            return render_template('dashboard.html')
        except Exception as e:
            logger.error(f"Error rendering dashboard.html: {e}")
            return f"Error loading dashboard: {e}", 500
    
    @app.route('/bulk_results.html')
    def bulk_results_page():
        from flask import render_template
        try:
            return render_template('bulk_results.html')
        except Exception as e:
            logger.error(f"Error rendering bulk_results.html: {e}")
            return f"Error loading bulk results page: {e}", 500
    
    @app.route('/calculate')
    @app.route('/calculate.html')
    def calculate_page():
        from flask import render_template
        try:
            return render_template('calculate.html')
        except Exception as e:
            logger.error(f"Error rendering calculate.html: {e}")
            return f"Error loading calculate page: {e}", 500
    
    @app.route('/complete_lease_form')
    @app.route('/complete_lease_form.html')
    def lease_form_page():
        from flask import render_template
        try:
            return render_template('complete_lease_form.html')
        except Exception as e:
            logger.error(f"Error rendering complete_lease_form.html: {e}")
            return f"Error loading lease form: {e}", 500
    
    logger.info("✅ Application created successfully")
    logger.info(f"📂 Template folder: {app.template_folder}")
    logger.info(f"📂 Static folder: {app.static_folder}")
    return app


# Create app instance
app = create_app()


if __name__ == '__main__':
    logger = logging.getLogger(__name__)
    
    logger.info("══════════════════════════════════════════════════════════════")
    logger.info("   📊 Lease Management System - Starting Server")
    logger.info("══════════════════════════════════════════════════════════════")
    logger.info(f"📍 API Endpoint: http://localhost:{Config.API_PORT}/api/")
    logger.info("   - /api/register - User registration")
    logger.info("   - /api/login - User login")
    logger.info("   - /api/leases - Manage leases")
    logger.info("   - /api/calculate_lease - Calculate lease")
    logger.info(f"📝 Logs: {Config.LOG_DIR}/lease_app.log")
    logger.info("══════════════════════════════════════════════════════════════")
    
    app.run(
        debug=Config.DEBUG,
        host=Config.API_HOST,
        port=Config.API_PORT
    )

