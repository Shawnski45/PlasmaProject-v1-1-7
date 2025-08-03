import os
from flask import Blueprint, request, jsonify, current_app, session
from pymongo import MongoClient
from bson.objectid import ObjectId
from dotenv import load_dotenv

load_dotenv()

guest_checkout_bp = Blueprint('guest_checkout', __name__)

client = MongoClient(os.environ.get('MONGODB_URI'))
db_name = os.environ.get('MONGODB_DBNAME')
if db_name:
    db = client[db_name]
else:
    from urllib.parse import urlparse
    uri = os.environ.get('MONGODB_URI')
    parsed = urlparse(uri)
    path = parsed.path.lstrip('/')
    db = client[path] if path else client['plasmaproject']
users_collection = db['users']
orders_collection = db['orders']

@guest_checkout_bp.route('/guest_checkout', methods=['POST'])
def guest_checkout():
    data = request.json
    try:
        guest_doc = {
            'email': data['email'],
            'name': data['name'],
            'phone': data['phone'],
            'is_guest': True
        }
        user_id = users_collection.insert_one(guest_doc).inserted_id
        order_id = data.get('order_id')
        if order_id:
            orders_collection.update_one({'_id': ObjectId(order_id)}, {'$set': {'user_id': user_id}})
        session['user_id'] = str(user_id)
        return jsonify({'message': 'Guest checkout successful', 'user_id': str(user_id)})
    except Exception as e:
        current_app.logger.error(f"Guest checkout failed: {e}")
        return jsonify({'error': str(e)}), 400
