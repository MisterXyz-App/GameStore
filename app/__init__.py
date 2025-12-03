from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
import cloudinary
import cloudinary.uploader
import cloudinary.api
import os

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-123')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///games.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Cloudinary Configuration
    cloudinary.config(
        cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME', 'dzfkklsza'),
        api_key=os.environ.get('CLOUDINARY_API_KEY', '588474134734416'),
        api_secret=os.environ.get('CLOUDINARY_API_SECRET', '9c12YJe5rZSYSg7zROQuvmVZ7mg'),
        secure=True
    )
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    
    # Register context processors
    @app.context_processor
    def utility_processor():
        def get_game_count_by_category(category):
            from app.models import Game
            return Game.query.filter_by(category=category, is_active=True).count()
        
        def get_all_categories():
            from app.routes import get_categories
            return get_categories()
        
        return dict(
            get_game_count_by_category=get_game_count_by_category,
            get_all_categories=get_all_categories
        )
    
    # Register blueprints
    with app.app_context():
        from app.routes import main, auth, admin
        app.register_blueprint(main)
        app.register_blueprint(auth)
        app.register_blueprint(admin)
    
    return app