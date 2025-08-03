# PROOF: Always write this file so we know conftest.py was loaded by pytest
with open("pytest_conftest_check.txt", "w") as f:
    import sys, os
    f.write(f"PYTEST CONFTST CHECK\npython_executable={sys.executable}\ncwd={os.getcwd()}\n")

import pytest
from app import create_app, db as _db
from sqlalchemy.pool import StaticPool
import logging

# Configure logging at session start to also capture pytest errors
@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    file_handler = logging.FileHandler('error.log', mode='a', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)
    root_logger.setLevel(logging.INFO)
    # Add a marker to avoid duplicate handlers
    config._errorlog_file_handler = file_handler
    # Log a startup message to confirm pytest is using this conftest.py
    import sys, os
    root_logger.info('PYTEST STARTUP: conftest.py loaded and logging configured.')
    root_logger.info(f'PYTEST ENV: python_executable={sys.executable}, cwd={os.getcwd()}, VIRTUAL_ENV={os.environ.get("VIRTUAL_ENV")})'
    )
    # --- SCHEMA CHECK ---
    try:
        from app import db
        collections = db.list_collection_names()
        root_logger.info(f'MongoDB collections: {collections}')
    except Exception as e:
        root_logger.error(f'MongoDB test setup failed: {e}', exc_info=True)

# Log all test failures and errors to error.log
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if rep.when == 'call' and (rep.failed or rep.skipped):
        logger = logging.getLogger()
        logger.error(f"Test {item.nodeid} {rep.outcome.upper()}\nCaptured output:\n{rep.capstdout if hasattr(rep, 'capstdout') else ''}\nCaptured stderr:\n{rep.capstderr if hasattr(rep, 'capstderr') else ''}")
        if rep.longrepr:
            logger.error(f"Failure traceback for {item.nodeid}:\n{rep.longrepr}")

@pytest.fixture(scope='session')
def app():
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite://',
        'SQLALCHEMY_ENGINE_OPTIONS': {
            'connect_args': {'check_same_thread': False},
            'poolclass': StaticPool,
        }
    })
    return app

@pytest.fixture(scope='session')
def db(app):
    with app.app_context():
        _db.drop_all()
        _db.create_all()
    yield _db
    with app.app_context():
        _db.session.remove()
        _db.drop_all()

@pytest.fixture(scope='function')
def session(db, app):
    with app.app_context():
        connection = db.engine.connect()
        transaction = connection.begin()
        session = db.Session(bind=connection)
        yield session
        session.close()
        transaction.rollback()
        connection.close()
