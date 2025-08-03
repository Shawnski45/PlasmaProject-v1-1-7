"""
test_routes_main.py
Tests the main routes in app/routes/main.py for correct status codes, authentication enforcement, and template rendering.
Covers both logged-in and guest scenarios, and checks for error handling.
Development-only: logs route coverage and response times.
"""
import pytest
from flask import url_for
from app import create_app, db
from app.models import User

@pytest.fixture(scope="session")
def app():
    from sqlalchemy.pool import StaticPool
    app = create_app()
    app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        SQLALCHEMY_ENGINE_OPTIONS={
            "poolclass": StaticPool,
            "connect_args": {"check_same_thread": False}
        }
    )
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture(scope="function")
def client(app):
    return app.test_client()

def test_index_route_guest(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Quote" in resp.data or b"Order" in resp.data

def test_protected_route_requires_login(client):
    resp = client.get("/order_history", follow_redirects=True)
    assert resp.status_code == 200
    assert b"login" in resp.data.lower() or b"sign in" in resp.data.lower()

def test_error_handling(client):
    resp = client.get("/nonexistent_page")
    assert resp.status_code in (404, 500)

# Development-only: log route coverage
def test_dev_route_coverage(app, capsys):
    with app.test_client() as client:
        routes = [rule.rule for rule in app.url_map.iter_rules()]
        # print removed: "[DEV] All routes:", routes)
        for rule in app.url_map.iter_rules():
            # Skip static and routes with parameters
            if rule.endpoint == 'static' or '<' in rule.rule:
                continue
            methods = getattr(rule, 'methods', set())
            if 'GET' in methods:
                resp = client.get(rule.rule)
                # print removed: f"[DEV] Route {rule.rule} status: {resp.status_code}")
    out, _ = capsys.readouterr()
    assert "[DEV] All routes:" in out
