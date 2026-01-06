from flask import Flask, render_template, request, session, redirect, url_for
from pyngrok import ngrok, conf
import sqlite3
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
# Use environment variable, fallback to secure default
app.secret_key = os.getenv('SECRET_KEY', 'dev-key-change-in-production')

DB_PATH = 'beiradar.db'
PORT = 5000


# NGROK CONFIG

NGROK_PATH = r"C:\Users\Lilian Imma W\Downloads\ngrok-v3-stable-windows-amd64\ngrok.exe"

conf.get_default().ngrok_path = NGROK_PATH
ngrok.kill()

public_url = ngrok.connect(PORT)
print(f"Shareable Ngrok URL: {public_url}")

# DATABASE FUNCTIONS

def get_products(search_query=None, category=None, min_price=None, max_price=None, min_discount=None):
    """
    Fetch products from the database with optional filtering.
    Searches by BOTH product name AND category.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    sql = "SELECT rowid AS id, * FROM products"
    conditions = []
    params = []

    if search_query:
        # Search by product name OR category
        search_lower = f"%{search_query.lower()}%"
        conditions.append("(LOWER(product) LIKE ? OR LOWER(category) LIKE ?)")
        params.append(search_lower)
        params.append(search_lower)
    
    if category:
        conditions.append("LOWER(category) = ?")
        params.append(category.lower())

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()

    products = [dict(row) for row in rows]
    
    # Apply price and discount filtering (post-database)
    if min_price is not None or max_price is not None or min_discount is not None:
        filtered = []
        for p in products:
            best_price, _ = calculate_best_price(p)
            
            # Check price range
            if best_price:
                if min_price is not None and best_price < min_price:
                    continue
                if max_price is not None and best_price > max_price:
                    continue
            
            # Check discount
            if min_discount is not None:
                stores = ['Carrefour', 'Naivas', 'Quickmart']
                max_product_discount = 0
                for store in stores:
                    store_lower = store.lower()
                    current = p.get(f'{store_lower}_current')
                    original = p.get(f'{store_lower}_original')
                    
                    if current and original and original != '–':
                        try:
                            curr_f = float(current)
                            orig_f = float(original)
                            if orig_f > curr_f:
                                discount = (orig_f - curr_f) * 100 / orig_f
                                max_product_discount = max(max_product_discount, discount)
                        except:
                            pass
                
                if max_product_discount < min_discount:
                    continue
            
            filtered.append(p)
        products = filtered
    
    return products
def get_categories():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT category FROM products ORDER BY category")
    categories = [row[0] for row in cursor.fetchall()]
    conn.close()
    return categories

@app.context_processor
def utility_processor():
    return dict(get_categories=get_categories)

def get_cart():
    """Return the cart dict from session."""
    return session.get('cart', {})

def save_cart(cart):
    """Save the cart dict into session."""
    session['cart'] = cart

def add_to_cart(product_name, quantity=1):
    cart = get_cart()
    pname = str(product_name)
    if pname in cart:
        cart[pname] += quantity
    else:
        cart[pname] = quantity
    save_cart(cart)

def remove_from_cart(product_name):
    cart = get_cart()
    pname = str(product_name)
    if pname in cart:
        del cart[pname]
    save_cart(cart)

def update_cart(product_name, quantity):
    cart = get_cart()
    pname = str(product_name)
    if quantity <= 0:
        cart.pop(pname, None)
    else:
        cart[pname] = quantity
    save_cart(cart)


# PRICE CALCULATION FUNCTIONS

def calculate_best_price(product):
    """
    Calculate the best price from all stores.
    Returns None for best_store if all prices are the same.
    """
    stores = [
        ('Carrefour', product.get('carrefour_current')),
        ('Naivas', product.get('naivas_current')),
        ('Quickmart', product.get('quickmart_current'))
    ]
    
    # Filter out invalid prices
    valid_prices = [(store, price) for store, price in stores if price not in (None, 0)]
    
    if not valid_prices:
        return None, None
    
    # Find the best (minimum) price
    best_store, best_price = min(valid_prices, key=lambda x: x[1])
    
    # Check if all valid prices are the same
    unique_prices = set(price for _, price in valid_prices)
    
    # If all prices are the same, don't highlight any store as "best"
    if len(unique_prices) == 1:
        return best_price, None  # Return price but no best_store
    
    return best_price, best_store

def get_image_url(filename):
    """Returns the correct URL for a product image."""
    if not filename:
        return "https://via.placeholder.com/200?text=No+Image"
    
    filename = filename.replace("images/", "").strip()
    return url_for('static', filename=f'images/{filename}')

app.jinja_env.globals.update(get_image_url=get_image_url)

def process_products(products):
    """Process raw product data into display-friendly format"""
    processed = []

    for p in products:
        best_price, best_store = calculate_best_price(p)

        stores_data = {}
        for store_name in ['Carrefour', 'Naivas', 'Quickmart']:
            store_lower = store_name.lower()
            current = p.get(f'{store_lower}_current')
            original_raw = p.get(f'{store_lower}_original')

            if current is not None:
                try:
                    current = float(current)
                except:
                    current = None

            original = None
            if original_raw and original_raw != '–':
                try:
                    original = float(original_raw)
                except:
                    original = None

            discount = 0
            if current and original and original > current:
                discount = round((original - current) * 100 / original, 2)

            stores_data[store_name] = {
                'current': current,
                'original': original,
                'discount': discount,
                'display': f"KSh {current:,.0f}" if current else 'N/A'
            }

        processed.append({
            'id': p.get('id'),
            'name': p.get('product', 'Unknown Product'),
            'weight': p.get('weight', ''),
            'category': p.get('category', '').replace('_', ' ').title(),
            'best_price': best_price,
            'best_store': best_store,
            'stores': stores_data,
            'typical_price': p.get('cheapest_price'),
            'on_sale': any(d['discount'] > 0 for d in stores_data.values()),
            'image_url': p.get('image_url', ''),
            'is_discounted': bool(p.get('is_discounted_anywhere', 0))
        })

    return processed


# CART COMPARISON FUNCTIONS


def calculate_cart_totals_by_store(cart_items):
    """Calculate total cost for the cart at each supermarket."""
    stores = ['Carrefour', 'Naivas', 'Quickmart']
    store_totals = {store: 0 for store in stores}
    
    for item in cart_items:
        product = item['product_data']
        quantity = item['quantity']
        
        for store in stores:
            store_lower = store.lower()
            price = product.get(f'{store_lower}_current')
            if price:
                try:
                    store_totals[store] += float(price) * quantity
                except (ValueError, TypeError):
                    pass
    
    valid_totals = {k: v for k, v in store_totals.items() if v > 0}
    
    if valid_totals:
        best_store = min(valid_totals, key=valid_totals.get)
        best_price = valid_totals[best_store]
        max_savings = max(valid_totals.values()) - best_price
    else:
        best_store = None
        best_price = 0
        max_savings = 0
    
    return {
        'by_store': store_totals,
        'best_store': best_store,
        'best_price': best_price,
        'max_savings': max_savings,
        'has_all_stores': all(v > 0 for v in store_totals.values())
    }


# ROUTES

@app.route('/', methods=['GET'])
def home():
    """Home route with search and filtering"""
    query = request.args.get('search', '').strip()
    min_price = request.args.get('min_price')
    max_price = request.args.get('max_price')
    min_discount = request.args.get('min_discount')
    
    min_price = float(min_price) if min_price else None
    max_price = float(max_price) if max_price else None
    min_discount = float(min_discount) if min_discount else None

    if query:
        products = get_products(
            search_query=query,
            min_price=min_price,
            max_price=max_price,
            min_discount=min_discount
        )
        results = process_products(products)
    else:
        results = []

    return render_template(
        'index.html',
        query=query,
        products=results,
        min_price=min_price,
        max_price=max_price,
        min_discount=min_discount
    )

# Category mapping
CATEGORY_MAPPING = {
    "Rice": "Rice",
    "Cooking Oil": "Oil",
    "Sugar": "Sugar",
    "Milk": "Milk",
    "Yoghurt": "Yoghurt",
    "Cheese": "Cheese",
    "Laundry/Detergents": "Laundry/Detergents",
    "Dishwashing": "Dishwashing",
    "Paper products": "Paper products",
    "Toothpaste": "Toothpaste",
    "Lotion": "Lotion",
    "Sanitary Pads": "Sanitary Pads"
}

CATEGORIES = {
    "Foodstuff": ["Rice", "Cooking Oil", "Sugar"],
    "Dairy": ["Milk", "Yoghurt", "Cheese"],
    "Household": ["Laundry", "Dishwashing", "Paper products"],
    "Personal Care": ["Toothpastes", "Lotion", "Sanitary Pads"]
}

@app.route('/api/search-suggestions')
def search_suggestions():
    """API endpoint for autocomplete - Returns products AND categories"""
    query = request.args.get('q', '').strip().lower()
    
    if not query or len(query) < 2:
        return {'suggestions': []}
    
    suggestions = []
    seen = set()
    
    # Get matching products
    products = get_products(search_query=query)
    
    for p in products[:10]:  # Limit to 10 products
        product_name = p.get('product', '').strip()
        if product_name and product_name.lower() not in seen:
            suggestions.append({
                'text': product_name,
                'type': 'product'
            })
            seen.add(product_name.lower())
    
    # Get matching categories
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT DISTINCT category FROM products WHERE LOWER(category) LIKE ? ORDER BY category",
        (f"%{query}%",)
    )
    categories = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    for category in categories:
        category_display = category.replace('_', ' ').title()
        if category_display.lower() not in seen:
            suggestions.append({
                'text': category_display,
                'type': 'category'
            })
            seen.add(category_display.lower())
    
    # Return formatted suggestions (limit to 12 total)
    return {
        'suggestions': suggestions[:12]
    }
@app.route("/categories")
def categories_list():
    categories = [{"name": name, "slug": name.lower().replace(" ", "-")} for name in CATEGORIES.keys()]
    return render_template("categories.html", categories=categories)

@app.route("/categories/<category_slug>")
def category_detail(category_slug):
    category_name = None
    for name in CATEGORIES.keys():
        if name.lower().replace(" ", "-") == category_slug:
            category_name = name
            break

    if not category_name:
        return "Category not found", 404

    subcategories = CATEGORIES[category_name]
    return render_template("category_detail.html", category_name=category_name, subcategories=subcategories)

@app.route('/products/<subcategory_slug>')
def products_by_subcategory(subcategory_slug):
    """Show products in subcategory with filtering"""
    subcategory_name = subcategory_slug.replace('-', ' ').title()
    db_category = CATEGORY_MAPPING.get(subcategory_name, subcategory_name)
    
    min_price = request.args.get('min_price')
    max_price = request.args.get('max_price')
    min_discount = request.args.get('min_discount')
    
    min_price = float(min_price) if min_price else None
    max_price = float(max_price) if max_price else None
    min_discount = float(min_discount) if min_discount else None
    
    products = get_products(
        category=db_category,
        min_price=min_price,
        max_price=max_price,
        min_discount=min_discount
    )
    results = process_products(products)
    
    return render_template(
        'category_products.html',
        category_name=subcategory_name,
        products=results,
        min_price=min_price,
        max_price=max_price,
        min_discount=min_discount
    )


# CART ROUTES

@app.route("/cart")
def cart_view():
    """Cart view with multi-store totals"""
    cart = get_cart()
    products_in_cart = []

    for product_name, qty in cart.items():
        products = get_products(search_query=product_name)
        product = products[0] if products else None

        if product:
            processed = process_products([product])[0]
            products_in_cart.append({
                'name': processed['name'],
                'quantity': qty,
                'product_data': product,
                'best_price': processed['best_price'],
                'best_store': processed['best_store'],
                'stores': processed['stores'],
                'category': processed['category'],
                'image_url': processed['image_url']
            })

    cart_summary = calculate_cart_totals_by_store(products_in_cart) if products_in_cart else {
        'by_store': {'Carrefour': 0, 'Naivas': 0, 'Quickmart': 0},
        'best_store': None,
        'best_price': 0,
        'max_savings': 0,
        'has_all_stores': False
    }
    
    return render_template(
        "cart.html",
        products=products_in_cart,
        cart_summary=cart_summary
    )

@app.route("/cart/add/<product_name>", methods=['POST'])
def cart_add(product_name):
    """Add item to cart"""
    qty = int(request.form.get('quantity', 1))
    add_to_cart(product_name, qty)
    return redirect(request.referrer or url_for('home'))

@app.route("/cart/remove/<product_name>")
def cart_remove(product_name):
    """Remove item from cart"""
    remove_from_cart(product_name)
    return redirect(url_for('cart_view'))

@app.route("/cart/update/<product_name>", methods=['POST'])
def cart_update(product_name):
    """Update item quantity"""
    qty = int(request.form.get('quantity', 1))
    update_cart(product_name, qty)
    return redirect(url_for('cart_view'))


# OTHER ROUTES

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/deals')
def deals():
    """Show best deals"""
    products = get_products()
    deals_list = []
    
    for p in products:
        prices = {
            'Carrefour': p.get('carrefour_current'),
            'Naivas': p.get('naivas_current'),
            'Quickmart': p.get('quickmart_current')
        }
        
        valid_prices = {k: v for k, v in prices.items() if v and v > 0}
        
        if len(valid_prices) >= 2:
            best_store = min(valid_prices, key=valid_prices.get)
            best_price = valid_prices[best_store]
            max_price = max(valid_prices.values())
            
            if max_price > best_price:
                discount_pct = round((max_price - best_price) * 100 / max_price, 2)
                
                if discount_pct > 0:
                    deals_list.append({
                        'product_name': p.get('product', 'Unknown'),
                        'weight': p.get('weight', ''),
                        'store': best_store,
                        'old_price': max_price,
                        'new_price': best_price,
                        'deal_percentage': discount_pct,
                        'category': p.get('category', '').replace('_', ' ').title(),
                        'image_url': p.get('image_url', '')
                    })
    
    deals_list = sorted(deals_list, key=lambda x: x['deal_percentage'], reverse=True)
    return render_template('deals.html', deals=deals_list)

# CUSTOM FILTERS


@app.template_filter('safe_price')
def safe_price(value):
    """
    Safely format a price value, handling None and invalid values.
    Returns 'N/A' if value is None or invalid.
    """
    if value is None:
        return "N/A"
    try:
        return f"KSh {float(value):,.0f}"
    except (ValueError, TypeError):
        return "N/A"


# ERROR HANDLERS

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(e):
    return render_template('500.html'), 500


# RUN APP

if __name__ == '__main__':
    print(f"Visit your app locally: http://127.0.0.1:{PORT}")
    print(f"Shareable Ngrok URL: {public_url}")
    app.run(host="0.0.0.0", port=PORT, debug=True, use_reloader=False)