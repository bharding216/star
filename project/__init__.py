from datetime import timedelta
from flask import Flask, session, request, redirect, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask import g
from flask_session import Session
from flask_mail import Mail
import os
from helpers import generate_sitemap
from dotenv import load_dotenv
from project.utils.logging import configure_logging

db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()

def create_app(client_name='star'):
    app = Flask(__name__)

    # Load the correct .env file
    env_file = f'.env.{client_name}'
    if os.path.exists(env_file):
        load_dotenv(env_file)
        print(f"Loaded environment from {env_file}")
    else:
        print(f"Environment file {env_file} not found - using system environment variables")

    # Configure Flask to handle HTTP/2
    app.config['SERVER_NAME'] = None  # Allow any host
    app.config['PREFERRED_URL_SCHEME'] = 'http'  # Use HTTP for local development
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

    app.jinja_env.globals.update(generate_sitemap = generate_sitemap)

    # Configure app settings from Config class
    try:
        if client_name == 'star':
            from project.config.star import Config
            app.config.from_object(Config)
        elif client_name == 'se_legacy':
            from project.config.se_legacy import Config
            app.config.from_object(Config)
        else:
            raise ValueError(f"Unknown client_name: {client_name}")
        print(f"Loaded config for client: {client_name}")
    except ImportError as e:
        print(f"Failed to import config for {client_name}: {e}")
        raise

    # Set secret key for session management
    app.config['SECRET_KEY'] = os.getenv('secret_key', '')

    # Mail config settings for AWS SES:
    app.config['MAIL_SERVER'] = os.getenv('AWS_SES_MAIL_SERVER')
    app.config['MAIL_PORT'] = 587 
    app.config['MAIL_USERNAME'] = os.getenv('AWS_SES_SMTP_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('AWS_SES_SMTP_PASSWORD')
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_DEFAULT_SENDER'] = ('STX Resources', Config.SURMOUNT_GENERAL_EMAIL)

    # DB Config
    postgres_user = os.getenv('postgres_user', '')
    postgres_password = os.getenv('postgres_password', '')
    postgres_host = os.getenv('postgres_host', '')
    postgres_db = os.getenv('postgres_db', '')
    
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        f'postgresql+psycopg2://{postgres_user}:{postgres_password}@{postgres_host}/{postgres_db}'
    )

    app.config['SQLALCHEMY_POOL_SIZE'] = 5
    app.config['SQLALCHEMY_POOL_RECYCLE'] = 450
    app.config['SQLALCHEMY_MAX_OVERFLOW'] = 2
    app.config['SQLALCHEMY_POOL_TIMEOUT'] = 20
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,  # enable connection pool pre-ping
    }

    db.init_app(app)
    mail.init_app(app)

    # Configure logging
    configure_logging(app, mail)

    with app.app_context():
        
        from .models import supplier_login, admin_login

        db.create_all()

        login_manager.init_app(app)
        # Use setattr to avoid type checking issues
        setattr(login_manager, 'login_view', "views.login_vendor")
        login_manager.login_message = ""
        login_manager.login_message_category = "error"

        @login_manager.user_loader
        def load_user(id):
            user_type = session.get('user_type')
            if user_type == 'supplier':
                user = supplier_login.query.filter_by(id = id).first()
            elif user_type == 'admin':
                user = admin_login.query.filter_by(id = id).first()
            else:
                user = None
            return user

        # For each view function, assign user=current_user.
        @app.context_processor
        def inject_user():
            return dict(
                user=current_user,
                client_name=client_name,
                domain='https://www.' + app.config['DOMAIN_NAME'],
                client_name_title=app.config['CLIENT_NAME_TITLE']
            )

        # Set user type at startup instead of using before_first_request
        @app.before_request
        def set_user_type():
            if 'user_type' not in session:
                session['user_type'] = None

        @app.before_request
        def redirect_to_https():
            # Ensure that all requests are secure (HTTPS)
            if not request.is_secure and request.host not in ['localhost:2000', 'localhost:2001']:
                return redirect(request.url.replace('http://', 'https://'), code=301)

        def handle_error(error):
            error_code = getattr(error, 'code', 500)  # Get the error code, default to 500
            return render_template('shared/error.html', error_code=error_code), error_code

        app.register_error_handler(404, handle_error)
        app.register_error_handler(500, handle_error)
        app.register_error_handler(400, handle_error)
        app.register_error_handler(403, handle_error)
        app.register_error_handler(401, handle_error)
        app.register_error_handler(405, handle_error)
        app.register_error_handler(503, handle_error)

        # Register blueprints
        from project.utils.blueprints import register_blueprints
        register_blueprints(app)

        return app