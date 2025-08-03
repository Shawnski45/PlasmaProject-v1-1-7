# LOGGING MUST BE CONFIGURED BEFORE ANY OTHER IMPORTS OR LOGGING USAGE
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('error.log', encoding='utf-8')
    ]
)

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from dotenv import load_dotenv
load_dotenv()

from pymongo import MongoClient
from firebase_admin import credentials, initialize_app

# MongoDB Atlas setup
mongodb_uri = os.getenv("MONGODB_URI")
db_name = os.getenv("MONGODB_DBNAME", "plasmaproject")
try:
    client = MongoClient(mongodb_uri)
    db = client[db_name]
    client.server_info()  # Test connection
    logging.info(f"Connected to MongoDB database: {db_name}")
except Exception as e:
    logging.error(f"MongoDB connection failed: {str(e)}")
    raise

required_env_vars = [
    "MONGODB_URI", "MONGODB_DBNAME", "FIREBASE_PROJECT_ID", "FIREBASE_PRIVATE_KEY_ID", "FIREBASE_PRIVATE_KEY",
    "FIREBASE_CLIENT_EMAIL", "FIREBASE_CLIENT_ID", "FIREBASE_CLIENT_CERT_URL", "STRIPE_SECRET_KEY", "STRIPE_PUBLIC_KEY",
    "FLASK_SECRET_KEY", "MAIL_SERVER", "MAIL_PORT", "MAIL_USERNAME", "MAIL_PASSWORD", "UPLOAD_FOLDER"
]
for var in required_env_vars:
    if os.environ.get(var):
        logging.info(f"Env var {var}: set")
    else:
        logging.warning(f"Env var {var}: MISSING")

# Firebase setup (centralized here)
firebase_cred = credentials.Certificate({
    "type": "service_account",
    "project_id": os.getenv("FIREBASE_PROJECT_ID"),
    "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
    "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace("\\n", "\n"),
    "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
    "client_id": os.getenv("FIREBASE_CLIENT_ID"),
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_CERT_URL")
})
firebase_app = initialize_app(firebase_cred, name='default')  # Store the app instance

from flask import Flask
from flask_login import LoginManager
from flask_mail import Mail

# PyMongo setup
from app import db  # Use the global db from MongoDB setup

mail = Mail()
login_manager = LoginManager()

from flask_cors import CORS

def create_app(config=None):
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get("FLASK_SECRET_KEY", "parser-secret-key-here")
    CORS(app, supports_credentials=True)
    app.config['TEMPLATES_AUTO_RELOAD'] = os.environ.get("TEMPLATES_AUTO_RELOAD", "true").lower() == "true"
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = int(os.environ.get("SEND_FILE_MAX_AGE_DEFAULT", 0))
    app.config['UPLOAD_FOLDER'] = os.environ.get("UPLOAD_FOLDER", os.path.join(app.instance_path, 'uploads'))
    app.config['MAIL_SERVER'] = os.environ.get("MAIL_SERVER", "")
    app.config['MAIL_PORT'] = int(os.environ.get("MAIL_PORT", 587))
    app.config['MAIL_USE_TLS'] = os.environ.get("MAIL_USE_TLS", "1") in ["1", "true", "True"]
    app.config['MAIL_USERNAME'] = os.environ.get("MAIL_USERNAME", "")
    app.config['MAIL_PASSWORD'] = os.environ.get("MAIL_PASSWORD", "")
    app.config['STRIPE_SECRET_KEY'] = os.environ.get("STRIPE_SECRET_KEY", "")
    app.config['STRIPE_PUBLIC_KEY'] = os.environ.get("STRIPE_PUBLIC_KEY", "")
    app.config['STRIPE_WEBHOOK_SECRET'] = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    # Ensure BASE_URL is always set for Stripe success/cancel URLs
    app.config['BASE_URL'] = os.environ.get("BASE_URL", "http://localhost:5000")
    logging.info(f"BASE_URL at app startup: {app.config['BASE_URL']}")
    logging.info(f"Stripe success_url will be: {app.config['BASE_URL']}/success?session_id={{CHECKOUT_SESSION_ID}}")
    logging.info(f"Stripe cancel_url will be: {app.config['BASE_URL']}/")

    if config:
        app.config.update(config)

    # Initialize extensions
    mail.init_app(app)
    login_manager.init_app(app)

    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    # Define user_loader (placeholder until User model is created)
    @login_manager.user_loader
    def load_user(user_id):
        try:
            from app.models.user import User
            return User.query.get(int(user_id))
        except Exception as e:
            logging.error(f"Failed to load user with id {user_id}: {e}")
            return None

    # Error Handler
    @app.errorhandler(Exception)
    def handle_exception(e):
        import traceback
        tb = traceback.format_exc()
        logging.error(f"Exception: {e}\nTraceback:\n{tb}")
        return f"Exception: {e}\nTraceback:\n{tb}", 500

    # WSGI Middleware to log all errors
    class ErrorLoggingMiddleware:
        def __init__(self, app):
            self.app = app
        def __call__(self, environ, start_response):
            try:
                return self.app(environ, start_response)
            except Exception as e:
                import traceback
                tb = traceback.format_exc()
                logging.error(f"WSGI Exception: {e}\nTraceback:\n{tb}")
                raise
    app.wsgi_app = ErrorLoggingMiddleware(app.wsgi_app)

    # Register blueprints
    from .routes.main import main_bp
    app.register_blueprint(main_bp)
    from .routes.auth import auth_bp
    app.register_blueprint(auth_bp)
    from .routes.payments import payments_bp
    app.register_blueprint(payments_bp)
    from .routes.guest_checkout import guest_checkout_bp
    app.register_blueprint(guest_checkout_bp)
    # Register debug blueprint only in development
    debug_mode = os.environ.get('FLASK_DEBUG', '0') == '1' or os.environ.get('DEBUG', '0') == '1' or app.config.get('DEBUG', False)
    if debug_mode:
        from .routes.debug import debug_bp
        app.register_blueprint(debug_bp, name='debug_test')
        logging.info('Debug blueprint registered (development mode)')
    # Log all registered routes/methods for diagnostics
    for rule in app.url_map.iter_rules():
        logging.info(f"Registered route: {rule.rule} | methods={rule.methods} | endpoint={rule.endpoint}")
    logging.info(f"Registered blueprint endpoints: {[rule.endpoint for rule in app.url_map.iter_rules()]}")

    # Add test POST route for connectivity troubleshooting
    @app.route('/test_post', methods=['POST'])
    def test_post():
        logging.info(f"/test_post hit | method={request.method} | data={request.data}")
        return {'status': 'received'}, 200

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    logging.info(f"UPLOAD_FOLDER set to {app.config['UPLOAD_FOLDER']}")
    try:
        test_path = os.path.join(app.config['UPLOAD_FOLDER'], '.__cascade_test')
        with open(test_path, 'w') as f:
            f.write('test')
        os.remove(test_path)
        logging.info(f"UPLOAD_FOLDER is writable: {app.config['UPLOAD_FOLDER']}")
    except Exception as e:
        logging.error(f"UPLOAD_FOLDER is NOT writable: {app.config['UPLOAD_FOLDER']}, error: {e}")

    # Make Firebase app available to blueprints
    app.firebase_app = firebase_app

    return app