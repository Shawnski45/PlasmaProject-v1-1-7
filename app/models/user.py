from app import db
from datetime import datetime

def create_user(email, name):
    return db.users.insert_one({"email": email, "name": name, "created_at": datetime.utcnow()})

def get_user(email):
    return db.users.find_one({"email": email})
