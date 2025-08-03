
import sys
import os
import importlib.util
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    filename=os.path.join(os.path.dirname(__file__), '../diagnostics.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Environment variables check
def check_environment():
    env_vars = ["FLASK_ENV", "SECRET_KEY", "SQLALCHEMY_DATABASE_URI"]
    for key in env_vars:
        value = os.environ.get(key, "Not set")
        logger.info(f"Environment variable {key}: {value}")

# Dependency versions
def check_dependencies():
    dependencies = [
        ('ezdxf', 'DXF parsing'),
        ('shapely', 'Geometry processing'),
        ('flask', 'Web framework')
    ]
    for dep, purpose in dependencies:
        try:
            module = importlib.import_module(dep)
            logger.info(f"{dep} ({purpose}): {module.__version__}")
        except ImportError:
            logger.error(f"{dep} ({purpose}): Not installed")

# Database schema inspection
def check_database():
    try:
        from app import create_app, db
        from sqlalchemy import inspect
        app = create_app()
        with app.app_context():
            logger.info(f"Database URI: {db.engine.url}")
            if db.engine.url.drivername == 'sqlite':
                db_path = str(db.engine.url.database)
                logger.info(f"SQLite DB file: {db_path}, Exists: {os.path.exists(db_path)}")
            db.create_all()
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            if not tables:
                logger.warning("No tables found in the database")
            else:
                logger.info(f"Found {len(tables)} tables: {tables}")
                for table in tables:
                    columns = inspector.get_columns(table)
                    logger.info(f"Table {table}: {len(columns)} columns")
    except Exception as e:
        logger.error(f"Database schema inspection failed: {str(e)}")

# Upload folder permissions
def check_upload_folder():
    upload_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '../instance/uploads'))
    logger.info(f"Checking upload folder: {upload_folder}")
    try:
        Path(upload_folder).mkdir(parents=True, exist_ok=True)
        testfile = Path(upload_folder) / "diagnostics_testfile.txt"
        with open(testfile, "w") as f:
            f.write("test")
        with open(testfile, "r") as f:
            content = f.read()
        logger.info(f"Upload folder write/read test passed: {content}")
        os.remove(testfile)
    except Exception as e:
        logger.error(f"Upload folder test failed: {str(e)}")

# Log file status
def check_log_file():
    logfile = os.path.abspath(os.path.join(os.path.dirname(__file__), '../error.log'))
    logger.info(f"Checking log file: {logfile}")
    if os.path.exists(logfile):
        try:
            with open(logfile, "r") as f:
                lines = f.readlines()[-10:]
                logger.info(f"Log file exists, size: {os.path.getsize(logfile)} bytes")
                logger.info("Last 10 log lines:")
                for line in lines:
                    logger.info(line.rstrip())
        except Exception as e:
            logger.error(f"Could not read log file: {str(e)}")
    else:
        logger.warning("Log file does not exist")

# List test DXFs
def check_dxf_files():
    dxf_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../Inputs/primary_validation'))
    logger.info(f"Checking DXF directory: {dxf_dir}")
    if os.path.exists(dxf_dir):
        files = [f for f in os.listdir(dxf_dir) if f.lower().endswith('.dxf')]
        if files:
            logger.info(f"Found {len(files)} DXF files: {files}")
        else:
            logger.warning("No DXF files found in directory")
    else:
        logger.warning("DXF directory does not exist")

# Run all diagnostics
def run_diagnostics():
    logger.info("=== Starting PlasmaProject Diagnostics ===")
    check_environment()
    check_dependencies()
    check_database()
    check_upload_folder()
    check_log_file()
    check_dxf_files()
    logger.info("=== End Diagnostics ===")

if __name__ == "__main__":
    run_diagnostics()