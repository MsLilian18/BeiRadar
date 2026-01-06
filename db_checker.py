import sqlite3

DB_PATH = 'beiradar.db'

def check_database():
    """Check database structure and content"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("=" * 60)
    print("DATABASE DIAGNOSTIC")
    print("=" * 60)
    
    # Check if products table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='products'")
    table_exists = cursor.fetchone()
    
    if not table_exists:
        print("❌ ERROR: 'products' table does not exist!")
        conn.close()
        return
    
    print("✓ Table 'products' exists\n")
    
    # Get column names
    cursor.execute("PRAGMA table_info(products)")
    columns = cursor.fetchall()
    print(f"Columns in 'products' table ({len(columns)} total):")
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")
    
    print()
    
    # Count total products
    cursor.execute("SELECT COUNT(*) FROM products")
    total = cursor.fetchone()[0]
    print(f"Total products: {total}")
    
    if total == 0:
        print("❌ WARNING: No products in database!")
        conn.close()
        return
    
    print()
    
    # Show sample products
    cursor.execute("SELECT * FROM products LIMIT 3")
    rows = cursor.fetchall()
    col_names = [description[0] for description in cursor.description]
    
    print("Sample products:")
    for i, row in enumerate(rows, 1):
        print(f"\n--- Product {i} ---")
        for col_name, value in zip(col_names, row):
            print(f"  {col_name}: {value}")
    
    print()
    
    # Check for products with 'milk' in name
    cursor.execute("SELECT COUNT(*) FROM products WHERE LOWER(product) LIKE '%milk%'")
    milk_count = cursor.fetchone()[0]
    print(f"Products containing 'milk': {milk_count}")
    
    if milk_count > 0:
        cursor.execute("SELECT product FROM products WHERE LOWER(product) LIKE '%milk%' LIMIT 5")
        milk_products = cursor.fetchall()
        print("Sample milk products:")
        for prod in milk_products:
            print(f"  - {prod[0]}")
    
    print()
    
    # Check categories
    cursor.execute("SELECT DISTINCT category FROM products")
    categories = cursor.fetchall()
    print(f"Categories ({len(categories)} total):")
    for cat in categories:
        print(f"  - {cat[0]}")
    
    conn.close()
    print("\n" + "=" * 60)

if __name__ == '__main__':
    try:
        check_database()
    except sqlite3.OperationalError as e:
        print(f"❌ ERROR: Could not connect to database")
        print(f"   {e}")
        print("\nMake sure 'beiradar.db' exists in the current directory.")
    except Exception as e:
        print(f"❌ ERROR: {e}")