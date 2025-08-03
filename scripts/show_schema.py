import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import create_app, db
from sqlalchemy import inspect

app = create_app()
with app.app_context():
    print(f'Database URI: {db.engine.url}')
    # If using SQLite, check if file exists
    if db.engine.url.drivername == 'sqlite':
        db_path = str(db.engine.url.database)
        print(f'SQLite DB file: {db_path}')
        import os
        print(f'File exists: {os.path.exists(db_path)}')
    try:
        db.create_all()
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        if not tables:
            print('No tables found in the database.')
        else:
            print('Tables:')
            for t in tables:
                print(f'  {t}')
                columns = inspector.get_columns(t)
                for col in columns:
                    print(f'    - {col["name"]} ({col["type"]})')
    except Exception as e:
        print(f'Error inspecting schema: {e}')
