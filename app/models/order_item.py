from app import db
import uuid

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(36), db.ForeignKey('order.id'), nullable=False)
    cart_uid = db.Column(db.String(36), nullable=False, default=lambda: str(uuid.uuid4()), unique=True, index=True)
    part_number = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, default=0)
    material = db.Column(db.String(50), nullable=True)
    thickness = db.Column(db.Float, nullable=True)
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
    # Include any additional fields from the original models.py here.
