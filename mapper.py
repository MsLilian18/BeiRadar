import sqlite3
import os
import re
from difflib import SequenceMatcher

DB_PATH = 'beiradar.db'
IMAGE_FOLDER = 'static/images'

# Connect to database
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Fetch all products
cursor.execute("SELECT product FROM products")
products = [p[0] for p in cursor.fetchall()]

# List all images in folder
image_files = os.listdir(IMAGE_FOLDER)

# Manual mappings for difficult matches
MANUAL_MAPPINGS = {
    'Daawat Long Grain 5kg': 'dawaat lgrain 5kg',
    'Daawat Long Grain 1Kg': 'daawat lgrain 2kg',  # Use 2kg image if 1kg doesn't exist
    'Sunlight 2 in 1 Hand Washing Powder Lavender Sensations 500g': 'sunlight 2 in 1 Lavender 500g',
    'Kleenex Toilet Paper Roll White 8pcs': 'kleenex tpaper white 8pcs',
    'Molped Sanitary Pads Ultra Soft 16pcs': 'molped spads 16pcs',
    'Dabur Herbal Toothpaste Clove 150g': 'dabur clove toothpaste 150g',
    'Nice & Lovely Body Lotion Cocoa Butter 400ml': 'nice and lovely cocoa butter 400ml',
}

# Expanded abbreviations mapping
abbreviations = {
    'sberry': 'strawberry',
    'nat': 'natural',
    'mlk': 'milk',
    'pcs': 'pcs',
    'l': 'liter',
    'kg': 'kilogram',
    'g': 'gram',
    'ltr': 'liter',
    'tbsp': 'tablespoon',
    'tsp': 'teaspoon',
    'ml': 'milliliter',
    'oz': 'ounce',
    'fr': 'fresh',
    'veg': 'vegetable',
    'choc': 'chocolate',
    'straw': 'strawberry',
    'van': 'vanilla',
    'lgrain': 'long grain',
}

def clean_text(text):
    """Clean and normalize text for comparison"""
    text = text.lower()
    text = text.replace('-', ' ').replace('–', ' ').replace('_', ' ')
    text = text.replace('&', 'and')
    text = re.sub(r'[^a-z0-9\s]', '', text)
    
    # Expand abbreviations
    tokens = text.split()
    expanded = [abbreviations.get(tok, tok) for tok in tokens]
    return ' '.join(expanded)

def extract_key_terms(text):
    """Extract key terms (brand, product type, size) from text"""
    cleaned = clean_text(text)
    
    # Remove common filler words
    stopwords = {'the', 'a', 'an', 'and', 'or', 'of', 'for', 'with', 'in', 'hand', 'washing', 'powder'}
    tokens = [t for t in cleaned.split() if t not in stopwords and len(t) > 1]
    
    return tokens

def similarity_score(str1, str2):
    """Calculate similarity between two strings"""
    return SequenceMatcher(None, str1, str2).ratio()

def find_best_image(product_name, debug=False):
    """Find best matching image for a product"""
    # Check manual mappings first
    if product_name in MANUAL_MAPPINGS:
        target_filename = MANUAL_MAPPINGS[product_name]
        for img in image_files:
            img_name_no_ext = os.path.splitext(img)[0]
            if clean_text(img_name_no_ext) == clean_text(target_filename):
                return f"images/{img}"
            # Also try fuzzy match on manual mapping
            if clean_text(target_filename) in clean_text(img_name_no_ext) or clean_text(img_name_no_ext) in clean_text(target_filename):
                return f"images/{img}"
    
    product_clean = clean_text(product_name)
    product_tokens = extract_key_terms(product_name)
    
    best_match = None
    best_score = 0
    
    for img in image_files:
        img_name = os.path.splitext(img)[0]
        img_clean = clean_text(img_name)
        img_tokens = extract_key_terms(img_name)
        
        # Strategy 1: Exact match
        if product_clean == img_clean:
            return f"images/{img}"
        
        # Strategy 2: All product tokens in image
        if all(token in img_clean for token in product_tokens):
            return f"images/{img}"
        
        # Strategy 3: Score-based matching
        # Count matching tokens
        matching_tokens = sum(1 for token in product_tokens if token in img_tokens)
        token_ratio = matching_tokens / max(len(product_tokens), 1)
        
        # Calculate string similarity
        string_sim = similarity_score(product_clean, img_clean)
        
        # Combined score (weighted)
        score = (token_ratio * 0.7) + (string_sim * 0.3)
        
        if score > best_score and score > 0.48:  # Lowered threshold slightly
            best_score = score
            best_match = img
            
        if debug and score > 0.3:
            print(f"  {img_name}: token_ratio={token_ratio:.2f}, string_sim={string_sim:.2f}, score={score:.2f}")
    
    if best_match:
        return f"images/{best_match}"
    
    return None

# Update database with progress tracking
unmatched_products = []
matched_count = 0

print("Matching products to images...\n")

for i, product in enumerate(products, 1):
    image_path = find_best_image(product)
    
    if image_path:
        cursor.execute("""
            UPDATE products
            SET image_url = ?
            WHERE product = ?
        """, (image_path, product))
        matched_count += 1
        print(f"✓ [{i}/{len(products)}] Matched: {product} → {os.path.basename(image_path)}")
    else:
        unmatched_products.append(product)
        print(f"✗ [{i}/{len(products)}] No match: {product}")

conn.commit()
conn.close()

# Summary
print("\n" + "="*70)
print(f"SUMMARY:")
print(f"Total products: {len(products)}")
print(f"Matched: {matched_count}")
print(f"Unmatched: {len(unmatched_products)}")
print("="*70)

# Show unmatched products for manual review
if unmatched_products:
    print("\nProducts still needing manual review:")
    for p in unmatched_products:
        print(f" - {p}")
        # Show debug info for unmatched
        print(f"   Debug matches:")
        find_best_image(p, debug=True)
        print()
else:
    print("\n🎉 All products matched successfully!")

# Show available images that might be good candidates
if unmatched_products:
    print("\n" + "="*70)
    print("Available image files for reference:")
    print("="*70)
    for img in sorted(image_files):
        print(f"  - {img}")