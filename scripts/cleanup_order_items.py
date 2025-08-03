from pymongo import MongoClient

# Adjust the URI and DB name as needed for your environment
client = MongoClient("mongodb://localhost:27017")
db = client["plasma"]  # Replace with your actual DB name if different

# Remove any order_items that do not have a cart_uid field (i.e., are not valid cart items)
result = db.order_items.delete_many({"cart_uid": {"$exists": False}})
print(f"Deleted {result.deleted_count} invalid order_items.")
