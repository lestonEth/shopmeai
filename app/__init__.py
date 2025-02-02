from flask import Flask, jsonify, redirect, url_for, request
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_socketio import SocketIO
from datetime import timedelta

jwt = JWTManager()
cors = CORS()
socketio = SocketIO(cors_allowed_origins="*")

class StripeConfig:
    SECRET_KEY = "SECRET"
    STRIPE_PUBLISHABLE_KEY = "pk_test_51L7nq8GOhLaGDHrEc7mIskYioo0z3BPrhlH5GHsGeCjnTW0XHMxOPha3ZsnlgaRCD6LJe0iqqTDWPNv7x4TSEMUW002abkOl96"
    STRIPE_SECRET_KEY = "sk_test_51L7nq8GOhLaGDHrEWPhjujNs543pbkQdiAcHzFGrEsI706yOCY6pNxUvqAB1axWW4xRma34ddgsLj2Gy7UtZO8kc00FQ8Bti2z"

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your_secret_key'
    app.config['PREFERRED_URL_SCHEME'] = 'https'  # Enforce HTTPS in Flask-generated URLs

    # Force HTTPS for all incoming requests (redirect HTTP -> HTTPS)
    @app.before_request
    def force_https():
        if request.headers.get('X-Forwarded-Proto', 'http') == 'http':
            return redirect(request.url.replace("http://", "https://"), code=301)

    # JWT Configuration
    app.config['JWT_TOKEN_LOCATION'] = ['cookies']
    app.config['JWT_ACCESS_COOKIE_PATH'] = '/'
    app.config['JWT_REFRESH_COOKIE_PATH'] = '/token/refresh'
    app.config['JWT_COOKIE_CSRF_PROTECT'] = False
    app.config['JWT_COOKIE_SECURE'] = True  # Secure cookies for HTTPS
    app.config['JWT_ACCESS_COOKIE_NAME'] = "access_token"
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)
    app.config.from_object(StripeConfig())

    @jwt.expired_token_loader
    def expired_token_callback():
        return redirect(url_for('chat.admin_login'))

    # Upload Config
    UPLOAD_FOLDER = 'static/uploads' 
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'} 
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['ALLOWED_EXTENSIONS'] = ALLOWED_EXTENSIONS

    # Register Blueprints
    from .chat import chat as chat_blueprint
    app.register_blueprint(chat_blueprint)
    
    from .payment import payment as payment_blueprint
    app.register_blueprint(payment_blueprint, url_prefix="/payment")

    # Set CORS to allow all origins (or restrict to your ngrok domain)
    cors.init_app(app, resources={r"/*": {"origins": "*"}})

    # Initialize Extensions
    jwt.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*")  # Fix CORS issues

    return app
