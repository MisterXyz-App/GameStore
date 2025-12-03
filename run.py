from app import create_app, db
from app.models import User, Game, Order, PaymentMethod
from werkzeug.security import generate_password_hash
import os

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'User': User,
        'Game': Game,
        'Order': Order,
        'PaymentMethod': PaymentMethod
    }

def init_admin():
    """Create admin user if doesn't exist"""
    with app.app_context():
        # Check if User table exists and has any records
        try:
            admin_user = User.query.filter_by(email='admin@gamestore.com').first()
            if not admin_user:
                admin_user = User(
                    username='admin',
                    email='admin@gamestore.com',
                    password_hash=generate_password_hash('admin123'),
                    is_admin=True
                )
                db.session.add(admin_user)
                db.session.commit()
                print("✅ Admin user created: admin@gamestore.com / admin123")
            else:
                print("✅ Admin user already exists")
        except Exception as e:
            print(f"❌ Error creating admin user: {e}")

def init_sample_data():
    """Create sample data for testing"""
    with app.app_context():
        try:
            # Sample payment method
            if PaymentMethod.query.count() == 0:
                payment_methods = [
                    PaymentMethod(
                        name='BCA Transfer',
                        type='bank_transfer',
                        account_number='1234567890',
                        account_name='GAME STORE',
                        instructions='Transfer ke BCA dengan kode unik di deskripsi'
                    ),
                    PaymentMethod(
                        name='Gopay',
                        type='ewallet', 
                        account_number='081234567890',
                        account_name='GAME STORE',
                        instructions='Kirim ke nomor Gopay di atas'
                    )
                ]
                for pm in payment_methods:
                    db.session.add(pm)
                db.session.commit()
                print("✅ Sample payment methods created")

            # Sample games
            if Game.query.count() == 0:
                games = [
                    Game(
                        title='Space Adventure',
                        short_description='Epic space exploration game',
                        description='Embark on an incredible journey through the galaxy in this epic space exploration game. Discover new planets, battle alien forces, and build your interstellar empire.',
                        price=99000,
                        image_url='https://res.cloudinary.com/dzfkklsza/image/upload/v1700000000/space-adventure.jpg',
                        share_method='cloud_code',
                        cloud_code='SPACE2024',
                        stock=10,
                        category='Adventure',
                        is_active=True
                    ),
                    Game(
                        title='Racing Extreme',
                        short_description='High-speed racing game',
                        description='Experience the thrill of high-speed racing with realistic physics and stunning graphics. Compete in tournaments and unlock new cars and tracks.',
                        price=149000,
                        image_url='https://res.cloudinary.com/dzfkklsza/image/upload/v1700000000/racing-extreme.jpg',
                        share_method='account',
                        account_email='racing@game.com',
                        account_password='racing123',
                        stock=5,
                        category='Racing',
                        is_active=True
                    )
                ]
                for game in games:
                    db.session.add(game)
                db.session.commit()
                print("✅ Sample games created")
                
        except Exception as e:
            print(f"❌ Error creating sample data: {e}")

if __name__ == '__main__':
    with app.app_context():
        try:
            # Create tables
            db.create_all()
            print("✅ Database tables created")
            
            # Initialize data
            init_admin()
            init_sample_data()
            
        except Exception as e:
            print(f"❌ Error during initialization: {e}")
        
    print("🚀 Starting GameStore server...")
    app.run(debug=True, host='0.0.0.0', port=5000)