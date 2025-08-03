from app import db
import uuid

class Customer(db.Model):
    __tablename__ = 'customer'
    id = db.Column(db.String(36), primary_key=True, nullable=False, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(255), nullable=True)
    email = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    # Include any additional fields from the original models.py here.
