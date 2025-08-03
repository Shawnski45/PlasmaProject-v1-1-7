import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import db, create_app

app = create_app()
with app.app_context():
    from app.models import Order, OrderItem, Upload, User  # Direct import to ensure registration
    db.drop_all()
    db.create_all()
    print("Database recreated successfully.")
