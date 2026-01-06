import sqlite3

DB_PATH = 'beiradar.db'

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# See the first 10 products
cursor.execute("SELECT rowid, product, category, image_url FROM products LIMIT 10")
rows = cursor.fetchall()

for row in rows:
    print(f"ID: {row[0]}, Product: {row[1]}, Category: {row[2]}, Image: {row[3]}")

conn.close()
