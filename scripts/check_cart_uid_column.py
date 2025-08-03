import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import create_app, db
from sqlalchemy import inspect

app = create_app()

with app.app_context():
    inspector = inspect(db.engine)
    columns = inspector.get_columns('order_item')
    column_names = [col['name'] for col in columns]
    print('cart_uid' in column_names)
    print('Columns:', column_names)
