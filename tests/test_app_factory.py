"""
test_app_factory.py
Tests the app factory in app/__init__.py for correct configuration, extension initialization, and blueprint registration.
Reports extra config and blueprint info in development only.
"""
import pytest
from flask import Flask
from app import create_app, db, mail, login_manager

def test_create_app_returns_flask():
    app = create_app()
    assert isinstance(app, Flask), "create_app() should return a Flask app instance"

def test_extensions_initialized():
    app = create_app()
    with app.app_context():
        assert hasattr(db, 'session'), "db should be initialized with session"
        assert hasattr(mail, 'send'), "mail should be initialized with send"
        assert hasattr(login_manager, 'login_view'), "login_manager should be initialized"

def test_blueprints_registered():
    app = create_app()
    blueprints = list(app.blueprints.keys())
    assert 'main' in blueprints, "'main' blueprint should be registered"

# Development-only reporting
def test_dev_config_reporting(capfd):
    app = create_app()
    # print removed: "[DEV] Config keys:", list(app.config.keys()))
    # print removed: "[DEV] Blueprints:", list(app.blueprints.keys()))
    out, _ = capfd.readouterr()
    assert "[DEV] Config keys:" in out
    assert "[DEV] Blueprints:" in out
