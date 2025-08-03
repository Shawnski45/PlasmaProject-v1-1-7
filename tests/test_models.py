"""
test_models.py
Tests the ORM models in app/models.py for CRUD operations, relationships, and password hashing.
Development-only: prints model creation and relationship checks.
"""
import pytest
import sqlite3
from app import create_app, db
from app.models import User, Order, OrderItem, Upload

def print_db_state(label, app=None, engine=None, session=None):
    # print removed: f"\n[DB_STATE:{label}]")
    if app:
        # print removed: f"  id(app): {id(app)}")
    if engine:
        # print removed: f"  id(engine): {id(engine)} URI: {getattr(engine, 'url', None)}")
    if session:
        # print removed: f"  id(session): {id(session)} id(session.bind): {id(session.bind) if session.bind else None}")
    # # print removed: f"  Flask app context stack: {list(_app_ctx_stack._local.__dict__.keys())}")  # Removed for Flask 2.x compatibility
    # print removed: f"  Models: {list(db.metadata.tables.keys())}")
    # Try to fetch tables from sqlite_master if possible
    conn = None
    try:
        if session and session.bind:
            conn = session.bind.raw_connection()
        elif engine:
            conn = engine.raw_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            # print removed: f"  Tables in sqlite_master: {[t[0] for t in tables]}")
            cursor.close()
            conn.close()
    except Exception as e:
        # print removed: f"  [DB_STATE:{label}] Could not query sqlite_master: {e}")
    # print removed: "")


def test_user_crud(session):
    user = User(email="test@test.com", first_name="Test", last_name="User", phone="1234567890")
    user.set_password("password123")
    session.add(user)
    session.commit()
    fetched = session.query(User).filter_by(email="test@test.com").one()
    assert fetched.check_password("password123")
    assert not fetched.check_password("wrongpass")

def test_order_relationships(session):
    user = User(email="order@test.com", first_name="Order", last_name="Tester", phone="1234567890")
    user.set_password("pw")
    session.add(user)
    order = Order(id="ORD1", user=user, total=100.0)
    session.add(order)
    item = OrderItem(order=order, part_number="PN1", quantity=2, material="Steel", thickness=0.25)
    session.add(item)
    session.commit()
    fetched_order = session.query(Order).filter_by(id="ORD1").one()
    assert fetched_order.user.email == "order@test.com"
    assert fetched_order.items[0].part_number == "PN1"
    user = User(email="order@test.com", first_name="Order", last_name="Tester", phone="1234567890")
    user.set_password("pw")
    session.add(user)
    order = Order(id="ORD1", user=user, total=100.0)
    session.add(order)
    item = OrderItem(order=order, part_number="PN1", quantity=2, material="Steel", thickness=0.25)
    session.add(item)
    session.commit()
    fetched_order = session.query(Order).filter_by(id="ORD1").one()
    assert fetched_order.user.email == "order@test.com"
    assert fetched_order.items[0].part_number == "PN1"

# Development-only: print model summary
def test_dev_model_summary(session, capsys):
    user = User(email="dev@dev.com", first_name="Dev", last_name="Test", phone="1234567890")
    user.set_password("pw")
    session.add(user)
    session.commit()
    # print removed: f"[DEV] User created: {user.email}")
    out, _ = capsys.readouterr()
    assert "[DEV] User created:" in out
    user = User(email="dev@dev.com", first_name="Dev", last_name="Test", phone="1234567890")
    user.set_password("pw")
    session.add(user)
    session.commit()
    # print removed: f"[DEV] User created: {user.email}")
    out, _ = capsys.readouterr()
    assert "[DEV] User created:" in out
