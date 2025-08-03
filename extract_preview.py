import sqlite3
import json

conn = sqlite3.connect('instance/plasma.db')
cur = conn.cursor()

# Look for the Mandalorian/Star Wars part
cur.execute("SELECT part_number, preview FROM order_item WHERE part_number LIKE '%star%' OR part_number LIKE '%mandalorian%' ORDER BY id DESC LIMIT 1")
row = cur.fetchone()

if row:
    part, preview = row
    with open('mandalorian_preview.json', 'w', encoding='utf-8') as f:
        f.write(preview)
    print(f"Wrote preview JSON for {part} to mandalorian_preview.json. You can use this file directly in your SVG test viewer.")
else:
    print("No Mandalorian/Star Wars part found.")
