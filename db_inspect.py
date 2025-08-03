import os
from tabulate import tabulate
from app import create_app
from app import db
from app.models import User, Customer, Order, OrderItem, Upload

def print_table_data(model, logf):
    table = model.__tablename__
    rows = db.session.query(model).limit(5).all()
    logf.write(f"\nTable: {table} (showing up to 5 rows)\n")
    if rows:
        headers = [c.name for c in model.__table__.columns]
        data = [[getattr(row, c) for c in headers] for row in rows]
        logf.write(tabulate(data, headers=headers, tablefmt="grid") + "\n")
    else:
        logf.write("No rows found.\n")
    count = db.session.query(model).count()
    logf.write(f"Total rows: {count}\n")

def main():
    app = create_app()
    with app.app_context():
        with open("db_test_log.txt", "w", encoding="utf-8") as logf:
            engine = db.engine
            logf.write(f"Database URI: {engine.url}\n")
            inspector = db.inspect(engine)
            tables = inspector.get_table_names()
            logf.write(f"Tables found: {tables}\n")
            # Map table names to model classes
            model_map = {cls.__tablename__: cls for cls in [User, Customer, Order, OrderItem, Upload]}
            for table in tables:
                model = model_map.get(table)
                if model:
                    print_table_data(model, logf)
                else:
                    logf.write(f"No model found for table: {table}\n")
    print("Database inspection complete. See db_test_log.txt for results.")

if __name__ == "__main__":
    main()
