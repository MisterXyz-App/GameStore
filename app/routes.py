from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, session
from flask_login import login_required, current_user, login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from app import db
from app.models import Game, Order, OrderItem, PaymentMethod, User, UserLibrary
from app.forms import LoginForm, RegisterForm, GameForm, PaymentMethodForm, PaymentProofForm, AdminSettingsForm  # TAMBAH IMPORT
from app.utils.cloudinary_utils import upload_image, upload_payment_proof, delete_image
import os
from datetime import datetime
import json
import secrets
import uuid

# Define blueprints di awal file
main = Blueprint('main', __name__)
auth = Blueprint('auth', __name__)
admin = Blueprint('admin', __name__, url_prefix='/admin')

# Helper functions
def get_cart():
    cart = session.get('cart', [])
    # Ensure cart count is updated in session
    session['cart_count'] = len(cart)
    return cart

def save_cart(cart):
    session['cart'] = cart
    session['cart_count'] = len(cart)
    session.modified = True

def calculate_cart_total(cart):
    total = 0
    for item in cart:
        game = Game.query.get(item['game_id'])
        if game:
            total += game.price * item['quantity']
    return total

def get_categories():
    """Get all unique categories"""
    categories = db.session.query(Game.category).distinct().all()
    return [category[0] for category in categories if category[0]]

def get_game_count_by_category(category):
    """Get game count for a specific category"""
    return Game.query.filter_by(category=category, is_active=True).count()

def generate_access_code():
    """Generate unique access code for cloud code sharing"""
    return secrets.token_hex(8).upper()

# ==================== MAIN ROUTES ====================
@main.route('/')
def index():
    # Get all active games
    all_active_games = Game.query.filter_by(is_active=True).order_by(Game.created_at.desc()).all()
    
    # Group games by category for featured section
    featured_games_by_category = {}
    for game in all_active_games:
        if game.category not in featured_games_by_category:
            featured_games_by_category[game.category] = []
        if len(featured_games_by_category[game.category]) < 3:  # Max 3 per category
            featured_games_by_category[game.category].append(game)
    
    # Get popular games
    popular_games = Game.query.filter_by(is_active=True).limit(6).all()
    
    # Get categories for sidebar
    categories = get_categories()
    categories_with_counts = []
    for category in categories:
        categories_with_counts.append({
            'name': category,
            'count': get_game_count_by_category(category),
            'icon': 'cloud' if 'Cloud' in category or 'cloud' in category.lower() else 'fish'
        })
    
    return render_template('index.html', 
                         featured_games_by_category=featured_games_by_category,  # Changed this
                         popular_games=popular_games,
                         categories=categories_with_counts)

@main.route('/games')
def games():
    category = request.args.get('category')
    search = request.args.get('search')
    in_stock_only = request.args.get('in_stock')
    
    query = Game.query.filter_by(is_active=True)
    
    if category and category != 'all':
        query = query.filter_by(category=category)
    
    if search:
        query = query.filter(Game.title.ilike(f'%{search}%'))
    
    # Filter in stock only
    if in_stock_only:
        query = query.filter(Game.stock > 0)
    
    games = query.order_by(Game.created_at.desc()).all()
    categories = get_categories()
    
    # Prepare category data with counts
    categories_with_counts = []
    for category_item in categories:
        categories_with_counts.append({
            'name': category_item,
            'count': get_game_count_by_category(category_item)
        })
    
    return render_template('games.html', 
                         games=games, 
                         categories=categories_with_counts, 
                         current_category=category)

@main.route('/category/<category_name>')
def category_games(category_name):
    """Route khusus untuk kategori"""
    games = Game.query.filter_by(category=category_name, is_active=True).order_by(Game.created_at.desc()).all()
    categories = get_categories()
    
    # Prepare category data with counts
    categories_with_counts = []
    for category in categories:
        categories_with_counts.append({
            'name': category,
            'count': get_game_count_by_category(category)
        })
    
    return render_template('games.html', 
                         games=games, 
                         categories=categories_with_counts, 
                         current_category=category_name,
                         category_name=category_name)

@main.route('/game/<int:game_id>')
def game_detail(game_id):
    game = Game.query.get_or_404(game_id)
    in_library = False
    if current_user.is_authenticated:
        in_library = UserLibrary.query.filter_by(user_id=current_user.id, game_id=game_id).first() is not None
    
    # Cek stok
    stock_status = "In Stock" if game.stock > 0 else "Out of Stock"
    
    return render_template('game_detail.html', 
                         game=game, 
                         in_library=in_library,
                         stock_status=stock_status)

@main.route('/add-to-cart/<int:game_id>')
@login_required
def add_to_cart(game_id):
    game = Game.query.get_or_404(game_id)
    
    # Check if user already owns the game
    if UserLibrary.query.filter_by(user_id=current_user.id, game_id=game_id).first():
        flash('You already own this game!', 'warning')
        return redirect(request.referrer or url_for('main.games'))
    
    # Check stock availability
    if game.stock <= 0:
        flash(f'Sorry, {game.title} is out of stock!', 'error')
        return redirect(request.referrer or url_for('main.games'))
    
    cart = get_cart()
    
    # Check if game already in cart
    for item in cart:
        if item['game_id'] == game_id:
            # Check if adding more would exceed stock
            if item['quantity'] + 1 > game.stock:
                flash(f'Cannot add more. Only {game.stock} available in stock!', 'error')
                return redirect(request.referrer or url_for('main.games'))
            
            item['quantity'] += 1
            save_cart(cart)
            flash(f'{game.title} quantity updated in cart!', 'success')
            return redirect(request.referrer or url_for('main.games'))
    
    # Add new item to cart
    cart.append({
        'game_id': game_id,
        'title': game.title,
        'price': float(game.price),
        'quantity': 1,
        'image_url': game.image_url,
        'stock': game.stock  # Simpan info stok di cart
    })
    
    save_cart(cart)
    flash(f'{game.title} added to cart!', 'success')
    return redirect(request.referrer or url_for('main.games'))

@main.route('/buy-now/<int:game_id>', methods=['GET', 'POST'])
@login_required
def buy_now(game_id):
    """Buy immediately without adding to cart"""
    game = Game.query.get_or_404(game_id)
    
    # Check if user already owns the game
    if UserLibrary.query.filter_by(user_id=current_user.id, game_id=game_id).first():
        flash('You already own this game!', 'warning')
        return redirect(url_for('main.library'))
    
    # Check stock availability
    if game.stock <= 0:
        flash(f'Sorry, {game.title} is out of stock!', 'error')
        return redirect(url_for('main.game_detail', game_id=game_id))
    
    if request.method == 'POST':
        form = PaymentProofForm()
        payment_methods = PaymentMethod.query.filter_by(is_active=True).all()
        form.payment_method.choices = [(str(pm.id), f"{pm.name} - {pm.account_number} ({pm.type})") for pm in payment_methods]
        
        if form.validate_on_submit():
            payment_proof_url = None
            payment_proof_public_id = None
            
            # Upload payment proof to Cloudinary
            if form.proof_image.data:
                upload_result = upload_payment_proof(form.proof_image.data, folder="game_store/payment_proofs")
                if upload_result['success']:
                    payment_proof_url = upload_result['url']
                    payment_proof_public_id = upload_result['public_id']
                else:
                    flash('Failed to upload payment proof. Please try again.', 'error')
                    return render_template('buy_now.html', form=form, game=game)
            
            try:
                # Create order
                order = Order(
                    user_id=current_user.id,
                    total_amount=game.price,
                    payment_method=form.payment_method.data,
                    payment_proof_url=payment_proof_url,
                    payment_proof_public_id=payment_proof_public_id
                )
                
                db.session.add(order)
                db.session.flush()  # Flush untuk mendapatkan order.id
                
                # Add order item
                order_item = OrderItem(
                    order_id=order.id,
                    game_id=game.id,
                    quantity=1,
                    price=game.price
                )
                db.session.add(order_item)
                
                # Kurangi stok
                game.stock -= 1
                
                db.session.commit()
                
                flash('Order created successfully! Please wait for payment verification.', 'success')
                return redirect(url_for('main.order_success', order_id=order.id))
                
            except Exception as e:
                db.session.rollback()
                flash('Error creating order. Please try again.', 'error')
                print(f"Error in buy_now: {e}")
                return render_template('buy_now.html', form=form, game=game)
    else:
        form = PaymentProofForm()
        payment_methods = PaymentMethod.query.filter_by(is_active=True).all()
        form.payment_method.choices = [(str(pm.id), f"{pm.name} - {pm.account_number} ({pm.type})") for pm in payment_methods]
    
    return render_template('buy_now.html', form=form, game=game)

@main.route('/cart')
@login_required
def cart():
    cart_items = get_cart()
    games_in_cart = []
    total = 0
    
    for item in cart_items:
        game = Game.query.get(item['game_id'])
        if game:
            # Update stock info in cart
            item['stock'] = game.stock
            item_total = game.price * item['quantity']
            total += item_total
            games_in_cart.append({
                'game': game,
                'quantity': item['quantity'],
                'total': item_total,
                'max_quantity': min(item['quantity'], game.stock)  # Batasi quantity berdasarkan stok
            })
    
    save_cart(cart_items)  # Update cart dengan info stok terbaru
    
    return render_template('cart.html', cart_items=games_in_cart, total=total)

@main.route('/update-cart', methods=['POST'])
@login_required
def update_cart():
    cart = get_cart()
    game_id = int(request.form.get('game_id'))
    action = request.form.get('action')
    
    game = Game.query.get(game_id)
    if not game:
        flash('Game not found!', 'error')
        return redirect(url_for('main.cart'))
    
    for item in cart:
        if item['game_id'] == game_id:
            if action == 'increase':
                # Check stock before increasing
                if item['quantity'] + 1 > game.stock:
                    flash(f'Only {game.stock} available in stock!', 'error')
                else:
                    item['quantity'] += 1
            elif action == 'decrease' and item['quantity'] > 1:
                item['quantity'] -= 1
            elif action == 'remove':
                cart.remove(item)
            break
    
    save_cart(cart)
    return redirect(url_for('main.cart'))

@main.route('/clear-cart', methods=['POST'])
@login_required
def clear_cart():
    """Clear entire cart"""
    save_cart([])
    flash('Cart cleared!', 'info')
    return redirect(url_for('main.cart'))

@main.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart_items = get_cart()
    if not cart_items:
        flash('Your cart is empty!', 'warning')
        return redirect(url_for('main.cart'))
    
    # Check stock availability for all items in cart
    out_of_stock_items = []
    for item in cart_items:
        game = Game.query.get(item['game_id'])
        if game and game.stock < item['quantity']:
            out_of_stock_items.append(f"{game.title} (Available: {game.stock})")
    
    if out_of_stock_items:
        flash(f'Some items are out of stock: {", ".join(out_of_stock_items)}', 'error')
        return redirect(url_for('main.cart'))
    
    # Check if any games in cart are already owned
    owned_games = []
    for item in cart_items:
        if UserLibrary.query.filter_by(user_id=current_user.id, game_id=item['game_id']).first():
            owned_games.append(Game.query.get(item['game_id']).title)
    
    if owned_games:
        flash(f'You already own: {", ".join(owned_games)}. Please remove them from cart.', 'warning')
        return redirect(url_for('main.cart'))
    
    form = PaymentProofForm()
    payment_methods = PaymentMethod.query.filter_by(is_active=True).all()
    form.payment_method.choices = [(str(pm.id), f"{pm.name} - {pm.account_number} ({pm.type})") for pm in payment_methods]
    
    total = calculate_cart_total(cart_items)
    
    if form.validate_on_submit():
        payment_proof_url = None
        payment_proof_public_id = None
        
        # Upload payment proof to Cloudinary
        if form.proof_image.data:
            upload_result = upload_payment_proof(form.proof_image.data, folder="game_store/payment_proofs")
            if upload_result['success']:
                payment_proof_url = upload_result['url']
                payment_proof_public_id = upload_result['public_id']
            else:
                flash('Failed to upload payment proof. Please try again.', 'error')
                return render_template('checkout.html', form=form, total=total, cart_count=len(cart_items))
        
        try:
            # Create order
            order = Order(
                user_id=current_user.id,
                total_amount=total,
                payment_method=form.payment_method.data,
                payment_proof_url=payment_proof_url,
                payment_proof_public_id=payment_proof_public_id
            )
            
            db.session.add(order)
            db.session.flush()  # Flush untuk mendapatkan order.id
            
            # Add order items dan kurangi stok
            for item in cart_items:
                game = Game.query.get(item['game_id'])
                if game:
                    order_item = OrderItem(
                        order_id=order.id,
                        game_id=game.id,
                        quantity=item['quantity'],
                        price=game.price
                    )
                    db.session.add(order_item)
                    
                    # Kurangi stok
                    game.stock -= item['quantity']
            
            db.session.commit()
            
            # Clear cart
            save_cart([])
            
            flash('Order created successfully! Please wait for payment verification.', 'success')
            return redirect(url_for('main.order_success', order_id=order.id))
            
        except Exception as e:
            db.session.rollback()
            flash('Error creating order. Please try again.', 'error')
            print(f"Error in checkout: {e}")
            return render_template('checkout.html', form=form, total=total, cart_count=len(cart_items))
    
    return render_template('checkout.html', form=form, total=total, cart_count=len(cart_items))

@main.route('/order/success/<order_id>')
@login_required
def order_success(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id and not current_user.is_admin:
        flash('Access denied!', 'error')
        return redirect(url_for('main.index'))
    
    return render_template('order_success.html', order=order)

@main.route('/library')
@login_required
def library():
    user_library = UserLibrary.query.filter_by(user_id=current_user.id).all()
    return render_template('library.html', library=user_library)

@main.route('/download/<int:game_id>')
@login_required
def download_game(game_id):
    # Check if user owns the game
    library_item = UserLibrary.query.filter_by(user_id=current_user.id, game_id=game_id).first()
    if not library_item and not current_user.is_admin:
        flash('You do not own this game!', 'error')
        return redirect(url_for('main.library'))
    
    game = Game.query.get_or_404(game_id)
    
    # Update download count
    if library_item:
        library_item.download_count += 1
        
        # Jika belum ada access info, copy dari game atau generate baru
        if not library_item.access_code and game.share_method == 'cloud_code':
            # Generate unique access code untuk user ini
            library_item.access_code = generate_access_code()
        
        if not library_item.account_email and game.share_method == 'account':
            library_item.account_email = game.account_email
            library_item.account_password = game.account_password
        
        db.session.commit()
    
    return render_template('download.html', game=game, library_item=library_item)

@main.route('/payment-instructions')
def payment_instructions():
    payment_methods = PaymentMethod.query.filter_by(is_active=True).all()
    return render_template('payment_instructions.html', payment_methods=payment_methods)

@main.route('/api/cart-count')
def api_cart_count():
    """API endpoint to get current cart count"""
    cart_count = session.get('cart_count', 0)
    return jsonify({'count': cart_count})

@main.route('/search')
def search_games():
    """API endpoint for search"""
    query = request.args.get('q', '')
    if len(query) < 2:
        return jsonify([])
    
    games = Game.query.filter(
        Game.title.ilike(f'%{query}%'),
        Game.is_active == True
    ).limit(10).all()
    
    results = []
    for game in games:
        results.append({
            'id': game.id,
            'title': game.title,
            'category': game.category,
            'price': game.price,
            'image_url': game.image_url,
            'stock': game.stock,
            'url': url_for('main.game_detail', game_id=game.id)
        })
    
    return jsonify(results)

# ==================== AUTH ROUTES ====================

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            flash('Login successful!', 'success')
            return redirect(next_page or url_for('main.index'))
        else:
            flash('Login failed. Check your email and password.', 'error')
    
    return render_template('auth/login.html', form=form)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.confirm_password.data:
            flash('Passwords do not match!', 'error')
            return render_template('auth/register.html', form=form)
        
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already registered!', 'error')
            return render_template('auth/register.html', form=form)
        
        if User.query.filter_by(username=form.username.data).first():
            flash('Username already taken!', 'error')
            return render_template('auth/register.html', form=form)
        
        user = User(
            username=form.username.data,
            email=form.email.data,
            password_hash=generate_password_hash(form.password.data)
        )
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', form=form)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    # Clear cart session on logout
    session.pop('cart', None)
    session.pop('cart_count', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))

@auth.route('/profile')
@login_required
def profile():
    user_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).limit(5).all()
    return render_template('auth/profile.html', orders=user_orders)

# ==================== ADMIN ROUTES ====================

@admin.route('/')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access denied!', 'error')
        return redirect(url_for('main.index'))
    
    # Get all games for stock calculation
    all_games = Game.query.all()
    low_stock_games = len([g for g in all_games if 0 < g.stock <= 5])
    out_of_stock_games = len([g for g in all_games if g.stock <= 0])
    
    stats = {
        'total_orders': Order.query.count(),
        'pending_orders': Order.query.filter_by(status='pending').count(),
        'total_games': len(all_games),
        'total_users': User.query.count(),
        'total_revenue': db.session.query(db.func.sum(Order.total_amount)).filter_by(status='paid').scalar() or 0,
        'low_stock_games': low_stock_games,
        'out_of_stock_games': out_of_stock_games
    }
    
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html', stats=stats, recent_orders=recent_orders, games=all_games)

@admin.route('/settings', methods=['GET', 'POST'])
@login_required
def admin_settings():
    """Halaman untuk mengubah email dan password admin"""
    if not current_user.is_admin:
        flash('Access denied!', 'error')
        return redirect(url_for('main.index'))
    
    form = AdminSettingsForm(obj=current_user)
    
    if form.validate_on_submit():
        try:
            # Verify current password
            if not check_password_hash(current_user.password_hash, form.current_password.data):
                flash('Current password is incorrect!', 'error')
                return render_template('admin/settings.html', form=form)
            
            # Check if new password fields are filled
            if form.new_password.data:
                if form.new_password.data != form.confirm_password.data:
                    flash('New passwords do not match!', 'error')
                    return render_template('admin/settings.html', form=form)
                
                # Update password
                current_user.password_hash = generate_password_hash(form.new_password.data)
                flash('Password updated successfully!', 'success')
            
            # Check if email is already taken by another user
            if form.email.data != current_user.email:
                existing_user = User.query.filter_by(email=form.email.data).first()
                if existing_user and existing_user.id != current_user.id:
                    flash('Email already registered by another user!', 'error')
                    return render_template('admin/settings.html', form=form)
            
            # Check if username is already taken by another user
            if form.username.data != current_user.username:
                existing_user = User.query.filter_by(username=form.username.data).first()
                if existing_user and existing_user.id != current_user.id:
                    flash('Username already taken!', 'error')
                    return render_template('admin/settings.html', form=form)
            
            # Update user information
            current_user.username = form.username.data
            current_user.email = form.email.data
            
            db.session.commit()
            flash('Profile settings updated successfully!', 'success')
            return redirect(url_for('admin.admin_settings'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating settings: {str(e)}', 'error')
            print(f"Error in admin_settings: {e}")
    
    return render_template('admin/settings.html', form=form)

@admin.route('/orders')
@login_required
def admin_orders():
    if not current_user.is_admin:
        flash('Access denied!', 'error')
        return redirect(url_for('main.index'))
    
    status_filter = request.args.get('status', 'all')
    query = Order.query
    
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    orders = query.order_by(Order.created_at.desc()).all()
    return render_template('admin/orders.html', orders=orders, status_filter=status_filter)

@admin.route('/order/<order_id>')
@login_required
def admin_order_detail(order_id):
    if not current_user.is_admin:
        flash('Access denied!', 'error')
        return redirect(url_for('main.index'))
    
    order = Order.query.get_or_404(order_id)
    return render_template('admin/order_detail.html', order=order)

@admin.route('/verify-payment/<order_id>', methods=['POST'])
@login_required
def verify_payment(order_id):
    if not current_user.is_admin:
        flash('Access denied!', 'error')
        return redirect(url_for('main.index'))
    
    order = Order.query.get_or_404(order_id)
    action = request.form.get('action')
    
    try:
        if action == 'approve':
            order.status = 'paid'
            # Add games to user's library
            for item in order.items:
                # Check if user already has this game
                existing = UserLibrary.query.filter_by(user_id=order.user_id, game_id=item.game_id).first()
                if not existing:
                    # Get the game details
                    game = Game.query.get(item.game_id)
                    if not game:
                        continue  # Skip if game not found
                    
                    # Generate unique access info berdasarkan share method
                    access_code = None
                    account_email = None
                    account_password = None
                    
                    if game.share_method == 'cloud_code':
                        access_code = generate_access_code()
                    elif game.share_method == 'account':
                        account_email = game.account_email
                        account_password = game.account_password
                    
                    library_item = UserLibrary(
                        user_id=order.user_id, 
                        game_id=item.game_id,
                        access_code=access_code,
                        account_email=account_email,
                        account_password=account_password
                    )
                    db.session.add(library_item)
            
            flash('Payment approved! Games added to user library.', 'success')
            
        elif action == 'reject':
            order.status = 'cancelled'
            # Kembalikan stok jika order ditolak
            for item in order.items:
                game = Game.query.get(item.game_id)
                if game:
                    game.stock += item.quantity
            flash('Payment rejected! Stock has been restored.', 'warning')
        
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        flash('Error processing payment verification.', 'error')
        print(f"Error in verify_payment: {e}")
        # Debug lebih detail
        import traceback
        print(traceback.format_exc())
    
    return redirect(url_for('admin.admin_orders'))

@admin.route('/games')
@login_required
def admin_games():
    if not current_user.is_admin:
        flash('Access denied!', 'error')
        return redirect(url_for('main.index'))
    
    games = Game.query.order_by(Game.created_at.desc()).all()
    return render_template('admin/games.html', games=games)

@admin.route('/game/new', methods=['GET', 'POST'])
@login_required
def admin_add_game():
    if not current_user.is_admin:
        flash('Access denied!', 'error')
        return redirect(url_for('main.index'))
    
    form = GameForm()
    if form.validate_on_submit():
        image_url = None
        image_public_id = None
        
        # Handle image upload to Cloudinary
        if form.image_file.data:
            upload_result = upload_image(form.image_file.data, folder="game_store/games")
            if upload_result['success']:
                image_url = upload_result['url']
                image_public_id = upload_result['public_id']
            else:
                flash('Failed to upload image. Please try again.', 'error')
                return render_template('admin/game_form.html', form=form, title='Add New Game')
        
        # Use default image if no image uploaded
        if not image_url:
            image_url = 'https://res.cloudinary.com/dzfkklsza/image/upload/v1700000000/default-game.jpg'
        
        game = Game(
            title=form.title.data,
            description=form.description.data,
            short_description=form.short_description.data,
            price=form.price.data,
            image_url=image_url,
            image_public_id=image_public_id,
            
            # Fitur baru
            stock=form.stock.data,
            initial_stock=form.stock.data,
            share_method=form.share_method.data,
            cloud_code=form.cloud_code.data if form.share_method.data == 'cloud_code' else None,
            account_email=form.account_email.data if form.share_method.data == 'account' else None,
            account_password=form.account_password.data if form.share_method.data == 'account' else None,
            
            category=form.category.data,
            is_active=form.is_active.data
        )
        
        db.session.add(game)
        db.session.commit()
        
        flash('Game added successfully!', 'success')
        return redirect(url_for('admin.admin_games'))
    
    return render_template('admin/game_form.html', form=form, title='Add New Game')

@admin.route('/game/<int:game_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_game(game_id):
    if not current_user.is_admin:
        flash('Access denied!', 'error')
        return redirect(url_for('main.index'))
    
    game = Game.query.get_or_404(game_id)
    form = GameForm(obj=game)
    
    if form.validate_on_submit():
        # Handle new image upload
        if form.image_file.data:
            # Delete old image from Cloudinary if exists
            if game.image_public_id:
                delete_image(game.image_public_id)
            
            # Upload new image
            upload_result = upload_image(form.image_file.data, folder="game_store/games")
            if upload_result['success']:
                game.image_url = upload_result['url']
                game.image_public_id = upload_result['public_id']
            else:
                flash('Failed to upload image. Please try again.', 'error')
                return render_template('admin/game_form.html', form=form, title='Edit Game', game=game)
        
        game.title = form.title.data
        game.description = form.description.data
        game.short_description = form.short_description.data
        game.price = form.price.data
        
        # Update stok logika yang benar
        requested_stock = form.stock.data
        
        if requested_stock < game.stock:
            flash(f'Tidak bisa mengurangi stok dari {game.stock} ke {requested_stock}. Gunakan form restock hanya untuk menambah stok.', 'warning')
            return render_template('admin/game_form.html', form=form, title='Edit Game', game=game)
        
        # Jika menambah stok
        if requested_stock > game.stock:
            additional_stock = requested_stock - game.stock
            game.stock = requested_stock
            game.initial_stock += additional_stock
            flash(f'Stok ditambahkan sebanyak {additional_stock}. Total stok sekarang: {requested_stock}', 'info')
        
        game.share_method = form.share_method.data
        game.cloud_code = form.cloud_code.data if form.share_method.data == 'cloud_code' else None
        game.account_email = form.account_email.data if form.share_method.data == 'account' else None
        game.account_password = form.account_password.data if form.share_method.data == 'account' else None
        
        game.category = form.category.data
        game.is_active = form.is_active.data
        
        db.session.commit()
        flash('Game updated successfully!', 'success')
        return redirect(url_for('admin.admin_games'))
    
    return render_template('admin/game_form.html', form=form, title='Edit Game', game=game)

@admin.route('/game/<int:game_id>/restock', methods=['POST'])
@login_required
def admin_restock_game(game_id):
    if not current_user.is_admin:
        flash('Access denied!', 'error')
        return redirect(url_for('main.index'))
    
    game = Game.query.get_or_404(game_id)
    new_stock = request.form.get('new_stock', type=int)
    
    if new_stock is not None and new_stock >= 0:
        game.stock = new_stock
        db.session.commit()
        flash(f'Stock updated to {new_stock} for {game.title}', 'success')
    else:
        flash('Invalid stock quantity', 'error')
    
    return redirect(url_for('admin.admin_games'))

@admin.route('/game/<int:game_id>/delete', methods=['POST'])
@login_required
def admin_delete_game(game_id):
    if not current_user.is_admin:
        flash('Access denied!', 'error')
        return redirect(url_for('main.index'))
    
    game = Game.query.get_or_404(game_id)
    
    # Check if game has existing orders
    existing_orders = OrderItem.query.filter_by(game_id=game_id).first()
    if existing_orders:
        flash('Cannot delete game with existing orders!', 'error')
        return redirect(url_for('admin.admin_games'))
    
    # Delete image from Cloudinary
    if game.image_public_id:
        delete_image(game.image_public_id)
    
    db.session.delete(game)
    db.session.commit()
    
    flash('Game deleted successfully!', 'success')
    return redirect(url_for('admin.admin_games'))

@admin.route('/payment-methods')
@login_required
def admin_payment_methods():
    if not current_user.is_admin:
        flash('Access denied!', 'error')
        return redirect(url_for('main.index'))
    
    payment_methods = PaymentMethod.query.all()
    return render_template('admin/payment_methods.html', payment_methods=payment_methods)

@admin.route('/payment-method/new', methods=['GET', 'POST'])
@login_required
def admin_add_payment_method():
    if not current_user.is_admin:
        flash('Access denied!', 'error')
        return redirect(url_for('main.index'))
    
    form = PaymentMethodForm()
    if form.validate_on_submit():
        qr_code_url = None
        qr_code_public_id = None
        
        # Handle QR code upload
        if form.qr_code_file.data:
            upload_result = upload_image(form.qr_code_file.data, folder="game_store/qr_codes")
            if upload_result['success']:
                qr_code_url = upload_result['url']
                qr_code_public_id = upload_result['public_id']
        
        payment_method = PaymentMethod(
            name=form.name.data,
            type=form.type.data,
            account_number=form.account_number.data,
            account_name=form.account_name.data,
            qr_code_url=qr_code_url,
            qr_code_public_id=qr_code_public_id,
            instructions=form.instructions.data,
            is_active=form.is_active.data
        )
        
        db.session.add(payment_method)
        db.session.commit()
        
        flash('Payment method added successfully!', 'success')
        return redirect(url_for('admin.admin_payment_methods'))
    
    return render_template('admin/payment_method_form.html', form=form, title='Add Payment Method')

@admin.route('/payment-method/<int:method_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_payment_method(method_id):
    if not current_user.is_admin:
        flash('Access denied!', 'error')
        return redirect(url_for('main.index'))
    
    payment_method = PaymentMethod.query.get_or_404(method_id)
    form = PaymentMethodForm(obj=payment_method)
    
    if form.validate_on_submit():
        # Handle new QR code upload
        if form.qr_code_file.data:
            # Delete old QR code if exists
            if payment_method.qr_code_public_id:
                delete_image(payment_method.qr_code_public_id)
            
            # Upload new QR code
            upload_result = upload_image(form.qr_code_file.data, folder="game_store/qr_codes")
            if upload_result['success']:
                payment_method.qr_code_url = upload_result['url']
                payment_method.qr_code_public_id = upload_result['public_id']
        
        payment_method.name = form.name.data
        payment_method.type = form.type.data
        payment_method.account_number = form.account_number.data
        payment_method.account_name = form.account_name.data
        payment_method.instructions = form.instructions.data
        payment_method.is_active = form.is_active.data
        
        db.session.commit()
        flash('Payment method updated successfully!', 'success')
        return redirect(url_for('admin.admin_payment_methods'))
    
    return render_template('admin/payment_method_form.html', form=form, title='Edit Payment Method', payment_method=payment_method)

@admin.route('/payment-method/<int:method_id>/delete', methods=['POST'])
@login_required
def admin_delete_payment_method(method_id):
    if not current_user.is_admin:
        flash('Access denied!', 'error')
        return redirect(url_for('main.index'))
    
    payment_method = PaymentMethod.query.get_or_404(method_id)
    
    # Delete QR code from Cloudinary
    if payment_method.qr_code_public_id:
        delete_image(payment_method.qr_code_public_id)
    
    db.session.delete(payment_method)
    db.session.commit()
    
    flash('Payment method deleted successfully!', 'success')
    return redirect(url_for('admin.admin_payment_methods'))

@admin.route('/users')
@login_required
def admin_users():
    if not current_user.is_admin:
        flash('Access denied!', 'error')
        return redirect(url_for('main.index'))
    
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)

@admin.route('/user/<int:user_id>/toggle-admin', methods=['POST'])
@login_required
def admin_toggle_admin(user_id):
    if not current_user.is_admin:
        flash('Access denied!', 'error')
        return redirect(url_for('main.index'))
    
    user = User.query.get_or_404(user_id)
    
    # Prevent removing admin from yourself
    if user.id == current_user.id:
        flash('You cannot remove admin privileges from yourself!', 'error')
        return redirect(url_for('admin.admin_users'))
    
    user.is_admin = not user.is_admin
    db.session.commit()
    
    action = "granted" if user.is_admin else "revoked"
    flash(f'Admin privileges {action} for {user.username}', 'success')
    return redirect(url_for('admin.admin_users'))

@admin.route('/user/<int:user_id>/delete', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    if not current_user.is_admin:
        flash('Access denied!', 'error')
        return redirect(url_for('main.index'))
    
    user = User.query.get_or_404(user_id)
    
    # Prevent deleting yourself
    if user.id == current_user.id:
        flash('You cannot delete your own account!', 'error')
        return redirect(url_for('admin.admin_users'))
    
    # Check if user has orders
    user_orders = Order.query.filter_by(user_id=user_id).first()
    if user_orders:
        flash('Cannot delete user with existing orders!', 'error')
        return redirect(url_for('admin.admin_users'))
    
    db.session.delete(user)
    db.session.commit()
    
    flash('User deleted successfully!', 'success')
    return redirect(url_for('admin.admin_users'))

@admin.route('/reports/sales')
@login_required
def admin_sales_report():
    if not current_user.is_admin:
        flash('Access denied!', 'error')
        return redirect(url_for('main.index'))
    
    # Get sales data
    total_sales = db.session.query(db.func.sum(Order.total_amount)).filter_by(status='paid').scalar() or 0
    total_orders = Order.query.filter_by(status='paid').count()
    
    # Get popular games
    popular_games_data = db.session.query(
        Game.title, 
        db.func.sum(OrderItem.quantity).label('total_sold')
    ).select_from(OrderItem).join(Game, OrderItem.game_id == Game.id).join(Order, OrderItem.order_id == Order.id).filter(Order.status == 'paid').group_by(Game.id).order_by(db.desc('total_sold')).limit(5).all()
    
    popular_games = []
    for game_title, total_sold in popular_games_data:
        game = Game.query.filter_by(title=game_title).first()
        if game:
            popular_games.append({
                'title': game_title,
                'total_sold': total_sold,
                'revenue': total_sold * game.price
            })
    
    return render_template('admin/sales_report.html',
                         total_sales=total_sales,
                         total_orders=total_orders,
                         popular_games=popular_games)

# ==================== API ROUTES ====================

@main.route('/api/games')
def api_games():
    """API endpoint for games data"""
    games = Game.query.filter_by(is_active=True).all()
    result = []
    for game in games:
        result.append({
            'id': game.id,
            'title': game.title,
            'category': game.category,
            'price': game.price,
            'stock': game.stock,
            'image_url': game.image_url,
            'share_method': game.share_method
        })
    return jsonify(result)

@main.route('/api/order/<order_id>')
@login_required
def api_order_status(order_id):
    """API endpoint for order status"""
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id and not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    return jsonify({
        'id': order.id,
        'status': order.status,
        'total_amount': order.total_amount,
        'created_at': order.created_at.isoformat()
    })

@admin.route('/orders/search')
@login_required
def admin_search_orders():
    if not current_user.is_admin:
        flash('Access denied!', 'error')
        return redirect(url_for('main.index'))
    
    search_query = request.args.get('q', '')
    status_filter = request.args.get('status', 'all')
    
    # Build query
    query = Order.query.join(User)
    
    # Apply status filter
    if status_filter != 'all':
        query = query.filter(Order.status == status_filter)
    
    # Apply search
    if search_query:
        query = query.filter(
            db.or_(
                Order.id.ilike(f'%{search_query}%'),
                User.username.ilike(f'%{search_query}%'),
                User.email.ilike(f'%{search_query}%'),
                Order.payment_method.ilike(f'%{search_query}%')
            )
        )
    
    orders = query.order_by(Order.created_at.desc()).all()
    
    return render_template('admin/orders.html', 
                         orders=orders, 
                         status_filter=status_filter,
                         search_query=search_query)

# ==================== ERROR HANDLERS ====================

@main.app_errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@main.app_errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500

@main.app_errorhandler(403)
def forbidden_error(error):
    return render_template('errors/403.html'), 403

@main.app_errorhandler(401)
def unauthorized_error(error):
    flash('Please login to access this page.', 'error')
    return redirect(url_for('auth.login'))