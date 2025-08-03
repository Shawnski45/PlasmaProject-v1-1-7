import sqlite3
import json

# Connect to the database
conn = sqlite3.connect('plasma_project.db')
cur = conn.cursor()

# Query the last 3 OrderItems
cur.execute("SELECT id, part_number, preview FROM OrderItem ORDER BY id DESC LIMIT 3")
rows = cur.fetchall()

for row in rows:
    print(f"\nOrderItem ID: {row[0]}")
    print(f"Part Number: {row[1]}")
    preview = row[2]
    if preview:
        try:
            preview_json = json.loads(preview)
            print(f"Preview JSON (truncated): {str(preview_json)[:500]}")  # Print first 500 chars
        except Exception as e:
            print(f"Error decoding preview JSON: {e}")
            print(f"Raw preview: {preview[:500]}")
    else:
        print("No preview data.")

conn.close()
