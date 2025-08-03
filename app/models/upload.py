from app import db
from datetime import datetime

def create_upload(user_id, file_path):
    return db.uploads.insert_one({
        "user_id": user_id,
        "file_path": file_path,
        "created_at": datetime.utcnow()
    })

def get_user_uploads(user_id):
    return list(db.uploads.find({"user_id": user_id}))
