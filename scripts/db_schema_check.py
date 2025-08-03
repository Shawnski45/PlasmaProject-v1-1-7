"""
Quick DB Schema Check Script for Development
- Prints all tables and columns in the current SQLAlchemy database.
- Use this to verify that your pipeline creates all expected tables and that there are no mismatches for tests.
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import create_app, db

app = create_app()
with app.app_context():
    inspector = db.inspect(db.engine)
    tables = inspector.get_table_names()
    print("\nDatabase Tables:")
    for table in tables:
        print(f"- {table}")
        for col in inspector.get_columns(table):
            print(f"    {col['name']} ({col['type']})")
    if not tables:
        print("(No tables found. DB is empty or not initialized.)")
