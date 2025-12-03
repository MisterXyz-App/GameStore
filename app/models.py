from app import db, login_manager
from flask_login import UserMixin
from datetime import datetime
import uuid
import secrets

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    orders = db.relationship('Order', backref='user', lazy=True)
    library_items = db.relationship('UserLibrary', backref='user', lazy=True)

class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    short_description = db.Column(db.String(200))
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(500))
    image_public_id = db.Column(db.String(200))
    
    # Fitur baru: metode share game
    share_method = db.Column(db.String(20), default='cloud_code')  # 'cloud_code' atau 'account'
    cloud_code = db.Column(db.String(100))  # Kode cloud/phone
    account_email = db.Column(db.String(120))  # Email akun game
    account_password = db.Column(db.String(200))  # Password akun game
    
    # Fitur stok
    stock = db.Column(db.Integer, default=0)  # Stok tersedia
    initial_stock = db.Column(db.Integer, default=0)  # Stok awal
    
    category = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    order_items = db.relationship('OrderItem', backref='game', lazy=True)  # Changed from 'ordered_game' to 'game'
    library_items = db.relationship('UserLibrary', backref='game', lazy=True)

class Order(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')
    payment_method = db.Column(db.String(50))
    payment_proof_url = db.Column(db.String(500))
    payment_proof_public_id = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    items = db.relationship('OrderItem', backref='order', lazy=True)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(36), db.ForeignKey('order.id'), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    price = db.Column(db.Float, nullable=False)

class PaymentMethod(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50))
    account_number = db.Column(db.String(100))
    account_name = db.Column(db.String(100))
    qr_code_url = db.Column(db.String(500))
    qr_code_public_id = db.Column(db.String(200))
    instructions = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)

class UserLibrary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)
    purchased_at = db.Column(db.DateTime, default=datetime.utcnow)
    download_count = db.Column(db.Integer, default=0)
    
    # Informasi akses game
    access_code = db.Column(db.String(100))  # Kode akses untuk cloud code
    account_email = db.Column(db.String(120))  # Email akun yang dibagikan
    account_password = db.Column(db.String(200))  # Password akun yang dibagikan

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))