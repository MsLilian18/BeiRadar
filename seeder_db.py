import pandas as pd
import sqlite3

# Load your Excel files
files = {
    "oil": "Sort/Oil data.xlsx",
    "rice": "Sort/Rice Data.xlsx",
    "sugar": "Sort/Sugar data.xlsx",
    "milk": "Sort/Milk data.xlsx",
    "yoghurt": "Sort/Yoghurt data.xlsx",
    "cheese": "Sort/Cheese data.xlsx",
    "laundry": "Sort/Laundry data.xlsx",
    "dishwashing": "Sort/Dishwashing data.xlsx",
    "paper products": "Sort/Paper data.xlsx",
    "sanitary pads": "Sort/Sanitary Pads data.xlsx",
    "toothpastes": "Sort/Toothpaste data.xlsx",
    "lotion": "Sort/Lotion data.xlsx",


}

dfs = {}
for category, path in files.items():
    df = pd.read_excel(path)
    # Normalize column names
    df.columns = [c.lower().replace(' ', '_') for c in df.columns]
    
    # Add category column
    df['category'] = category
    
    # Optional: add extra columns
    df['image_url'] = ''
    df['is_discounted_anywhere'] = 1
    
    # Convert price columns to numeric
    for col in df.columns:
        if 'price' in col:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    dfs[category] = df

# Concatenate all products
all_products = pd.concat(dfs.values(), ignore_index=True)

# Insert into SQLite database
conn = sqlite3.connect('beiradar.db')
all_products.to_sql('products', conn, if_exists='replace', index=False)
conn.close()

print("Database updated successfully!")
