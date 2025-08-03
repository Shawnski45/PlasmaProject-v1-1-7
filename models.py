# PlasmaProject v1-1-5/models.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    company = db.Column(db.String(100), nullable=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20), nullable=False)  # Now required
    password_hash = db.Column(db.String(128), nullable=False)
    password_reset_token = db.Column(db.String(64), nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)


class Order(db.Model):
    id = db.Column(db.String(20), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=True)
    total = db.Column(db.Float, nullable=False)
    payment_intent_id = db.Column(db.String(50), unique=True, nullable=True)
    stripe_session_id = db.Column(db.String(255), nullable=True)  # Added for Stripe session ID
    status = db.Column(db.String(20), default='pending')
    purchase_date = db.Column(db.DateTime, default=db.func.now())
    shipped_date = db.Column(db.DateTime, nullable=True)
    company_name = db.Column(db.String(100), nullable=True)
    first_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    customer = db.relationship('Customer', backref=db.backref('orders', lazy=True))
    user = db.relationship('User', backref=db.backref('orders', lazy=True))
    items = db.relationship('OrderItem', backref='order', lazy=True)


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(20), db.ForeignKey('order.id'), nullable=False)
    part_number = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, default=0)
    material = db.Column(db.String(50), nullable=False)
    thickness = db.Column(db.Float, nullable=False)
    unit_price = db.Column(db.Float, default=0.0)
    cost_per_part = db.Column(db.Float, default=0.0)
    length = db.Column(db.Float, default=0.0)
    net_area_sqin = db.Column(db.Float, default=0.0)
    gross_area_sqin = db.Column(db.Float, default=0.0)
    net_weight_lb = db.Column(db.Float, default=0.0)
    outer_perimeter = db.Column(db.Float, default=0.0)
    gross_min_x = db.Column(db.Float, default=0.0)
    gross_min_y = db.Column(db.Float, default=0.0)
    gross_max_x = db.Column(db.Float, default=0.0)
    gross_max_y = db.Column(db.Float, default=0.0)
    gross_weight_lb = db.Column(db.Float, default=0.0)
    entity_count = db.Column(db.Integer, default=0)
    preview = db.Column(db.Text, nullable=True)
    pierce_count = db.Column(db.Integer, default=0)


class Upload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(20), db.ForeignKey('order.id'), nullable=False)
    file_path = db.Column(db.String(200), nullable=False)
