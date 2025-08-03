from app import db
from datetime import datetime

def get_order_items(order_id):
    return list(db.order_items.find({"order_id": order_id}))

def create_order(user_id, quote_details, payment_status):
    result = db.orders.insert_one({
        "user_id": user_id,
        "quote_details": quote_details,
        "payment_status": payment_status,
        "created_at": datetime.utcnow()
    })
    return db.orders.find_one({"_id": result.inserted_id})

def get_user_orders(user_id):
    return list(db.orders.find({"user_id": user_id}))
