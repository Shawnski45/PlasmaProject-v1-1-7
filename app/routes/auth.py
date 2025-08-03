from flask import Blueprint, request, jsonify, redirect, url_for, session
from firebase_admin import get_app, auth
from functools import wraps
import os

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Decorator to check if user is authenticated
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        id_token = session.get('id_token')
        if not id_token:
            return jsonify({"error": "Authentication required"}), 401
        try:
            firebase_app = get_app(name='default')
            auth.verify_id_token(id_token, app=firebase_app)  # Use named app
        except Exception as e:
            return jsonify({"error": str(e)}), 401
        return f(*args, **kwargs)
    return decorated_function

# Signup route (create user via Admin SDK)
@auth_bp.route('/signup', methods=['POST'])
def signup():
    try:
        email = request.json.get('email')
        password = request.json.get('password')
        firebase_app = get_app(name='default')
        user = auth.create_user(
            email=email,
            password=password,
            display_name="New User",
            app=firebase_app
        )
        return jsonify({"message": "User created successfully", "uid": user.uid}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Login route (verify token from client-side sign-in)
@auth_bp.route('/login', methods=['POST'])
def login():
    import logging
    try:
        logging.info(f"[AUTH] Incoming /auth/login request | JSON: {request.json}")
        id_token = request.json.get('id_token')
        if not id_token:
            logging.error("[AUTH] No id_token in request to /auth/login")
            return jsonify({"error": "Missing id_token"}), 400
        firebase_app = get_app(name='default')
        decoded_token = auth.verify_id_token(id_token, app=firebase_app)  # Use named app
        uid = decoded_token['uid']
        session['id_token'] = id_token
        session['user_email'] = decoded_token.get('email')
        logging.info(f"[AUTH] Firebase token verified | uid={uid}, email={decoded_token.get('email')}")
        return jsonify({"message": "Login successful", "uid": uid}), 200
    except Exception as e:
        logging.error(f"[AUTH] Error in /auth/login: {str(e)} | JSON: {request.json}", exc_info=True)
        return jsonify({"error": str(e)}), 400

# Logout route
@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    session.pop('id_token', None)
    return jsonify({"message": "Logout successful"}), 200

# Protected route example
@auth_bp.route('/protected', methods=['GET'])
@login_required
def protected():
    return jsonify({"message": "Protected route accessed"}), 200