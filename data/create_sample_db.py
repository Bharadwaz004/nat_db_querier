"""
Create a sample e-commerce SQLite database for the NL-to-SQL assistant.
Includes: customers, products, orders, order_items, categories, reviews, inventory.
"""
import sqlite3
import os
import random
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "sample_ecommerce.db")

def create_database():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # --- Schema ---
    cursor.executescript("""
    CREATE TABLE categories (
        category_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        description TEXT,
        parent_category_id INTEGER,
        FOREIGN KEY (parent_category_id) REFERENCES categories(category_id)
    );

    CREATE TABLE products (
        product_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        price REAL NOT NULL CHECK(price > 0),
        category_id INTEGER NOT NULL,
        brand TEXT,
        sku TEXT UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (category_id) REFERENCES categories(category_id)
    );

    CREATE TABLE customers (
        customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT,
        city TEXT,
        state TEXT,
        country TEXT DEFAULT 'US',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        order_date TIMESTAMP NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('pending','processing','shipped','delivered','cancelled','returned')),
        total_amount REAL NOT NULL,
        shipping_address TEXT,
        payment_method TEXT CHECK(payment_method IN ('credit_card','debit_card','paypal','bank_transfer')),
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
    );

    CREATE TABLE order_items (
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL CHECK(quantity > 0),
        unit_price REAL NOT NULL,
        discount REAL DEFAULT 0,
        FOREIGN KEY (order_id) REFERENCES orders(order_id),
        FOREIGN KEY (product_id) REFERENCES products(product_id)
    );

    CREATE TABLE reviews (
        review_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        customer_id INTEGER NOT NULL,
        rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
        title TEXT,
        comment TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (product_id) REFERENCES products(product_id),
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
    );

    CREATE TABLE inventory (
        inventory_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL UNIQUE,
        quantity_in_stock INTEGER NOT NULL DEFAULT 0,
        reorder_level INTEGER DEFAULT 10,
        warehouse_location TEXT,
        last_restocked TIMESTAMP,
        FOREIGN KEY (product_id) REFERENCES products(product_id)
    );
    """)

    # --- Seed Data ---
    categories = [
        (1, 'Electronics', 'Electronic devices and accessories', None),
        (2, 'Laptops', 'Portable computers', 1),
        (3, 'Smartphones', 'Mobile phones', 1),
        (4, 'Audio', 'Headphones, speakers, earbuds', 1),
        (5, 'Clothing', 'Apparel and fashion', None),
        (6, 'Men', "Men's clothing", 5),
        (7, 'Women', "Women's clothing", 5),
        (8, 'Home & Kitchen', 'Home appliances and kitchen tools', None),
        (9, 'Books', 'Physical and digital books', None),
        (10, 'Sports', 'Sports equipment and gear', None),
    ]
    cursor.executemany("INSERT INTO categories VALUES (?,?,?,?)", categories)

    brands = ['TechPro', 'SoundMax', 'UrbanStyle', 'HomeChef', 'FitGear', 'BookWorld', 'EliteWear', 'GadgetHub']
    product_data = [
        ('MacBook Pro 14"', 'High-performance laptop with M3 chip', 1999.99, 2, 'TechPro'),
        ('Dell XPS 15', 'Premium ultrabook with OLED display', 1549.99, 2, 'TechPro'),
        ('ThinkPad X1 Carbon', 'Business ultrabook', 1399.99, 2, 'TechPro'),
        ('iPhone 15 Pro', 'Latest smartphone with titanium design', 999.99, 3, 'TechPro'),
        ('Samsung Galaxy S24', 'AI-powered smartphone', 849.99, 3, 'GadgetHub'),
        ('Pixel 8 Pro', 'Google flagship phone', 899.99, 3, 'GadgetHub'),
        ('Sony WH-1000XM5', 'Premium noise-cancelling headphones', 349.99, 4, 'SoundMax'),
        ('AirPods Pro 2', 'True wireless earbuds with ANC', 249.99, 4, 'SoundMax'),
        ('Bose QC Ultra', 'Spatial audio headphones', 429.99, 4, 'SoundMax'),
        ('Classic Oxford Shirt', 'Premium cotton dress shirt', 79.99, 6, 'UrbanStyle'),
        ('Slim Fit Chinos', 'Stretch cotton chinos', 59.99, 6, 'UrbanStyle'),
        ('Wool Blazer', 'Italian wool blazer', 249.99, 6, 'EliteWear'),
        ('Silk Blouse', 'Elegant silk blouse', 129.99, 7, 'EliteWear'),
        ('Cashmere Sweater', 'Luxury cashmere pullover', 189.99, 7, 'EliteWear'),
        ('Yoga Leggings', 'High-waist performance leggings', 69.99, 7, 'FitGear'),
        ('Instant Pot Pro', '10-in-1 pressure cooker', 119.99, 8, 'HomeChef'),
        ('KitchenAid Mixer', 'Professional stand mixer', 379.99, 8, 'HomeChef'),
        ('Air Fryer XL', 'Large capacity air fryer', 89.99, 8, 'HomeChef'),
        ('Python Crash Course', 'Bestselling Python book', 39.99, 9, 'BookWorld'),
        ('Atomic Habits', 'Self-improvement bestseller', 16.99, 9, 'BookWorld'),
        ('Running Shoes Pro', 'Carbon-plate racing shoes', 179.99, 10, 'FitGear'),
        ('Yoga Mat Premium', 'Non-slip exercise mat', 49.99, 10, 'FitGear'),
        ('Resistance Bands Set', 'Full body workout set', 29.99, 10, 'FitGear'),
        ('Dumbbell Set 50lb', 'Adjustable dumbbell pair', 299.99, 10, 'FitGear'),
        ('Smart Watch Ultra', 'Fitness tracking smartwatch', 449.99, 3, 'GadgetHub'),
    ]

    for i, (name, desc, price, cat, brand) in enumerate(product_data, 1):
        sku = f"SKU-{cat:02d}-{i:04d}"
        cursor.execute(
            "INSERT INTO products (name, description, price, category_id, brand, sku) VALUES (?,?,?,?,?,?)",
            (name, desc, price, cat, brand, sku)
        )

    first_names = ['James','Mary','Robert','Patricia','John','Jennifer','Michael','Linda','David','Elizabeth',
                   'William','Barbara','Richard','Susan','Joseph','Jessica','Thomas','Sarah','Charles','Karen',
                   'Raj','Priya','Amit','Sneha','Wei','Mei','Carlos','Sofia','Ahmed','Fatima']
    last_names = ['Smith','Johnson','Williams','Brown','Jones','Garcia','Miller','Davis','Rodriguez','Martinez',
                  'Anderson','Taylor','Thomas','Hernandez','Moore','Jackson','Lee','White','Harris','Clark']
    cities = [('New York','NY'),('Los Angeles','CA'),('Chicago','IL'),('Houston','TX'),('Phoenix','AZ'),
              ('Philadelphia','PA'),('San Antonio','TX'),('San Diego','CA'),('Dallas','TX'),('Austin','TX'),
              ('Seattle','WA'),('Denver','CO'),('Boston','MA'),('Portland','OR'),('Miami','FL')]

    random.seed(42)
    for i in range(60):
        fn = random.choice(first_names)
        ln = random.choice(last_names)
        city, state = random.choice(cities)
        email = f"{fn.lower()}.{ln.lower()}{i}@email.com"
        phone = f"+1-{random.randint(200,999)}-{random.randint(100,999)}-{random.randint(1000,9999)}"
        created = datetime(2023, 1, 1) + timedelta(days=random.randint(0, 500))
        cursor.execute(
            "INSERT INTO customers (first_name, last_name, email, phone, city, state, created_at) VALUES (?,?,?,?,?,?,?)",
            (fn, ln, email, phone, city, state, created.isoformat())
        )

    statuses = ['pending','processing','shipped','delivered','delivered','delivered','cancelled','returned']
    payments = ['credit_card','debit_card','paypal','bank_transfer']

    for i in range(200):
        cust_id = random.randint(1, 60)
        order_date = datetime(2023, 6, 1) + timedelta(days=random.randint(0, 600))
        status = random.choice(statuses)
        payment = random.choice(payments)
        n_items = random.randint(1, 4)
        total = 0
        items = []
        for _ in range(n_items):
            prod_id = random.randint(1, 25)
            qty = random.randint(1, 3)
            cursor.execute("SELECT price FROM products WHERE product_id=?", (prod_id,))
            price = cursor.fetchone()[0]
            discount = random.choice([0, 0, 0, 0.05, 0.1, 0.15, 0.2])
            unit_price = round(price * (1 - discount), 2)
            total += unit_price * qty
            items.append((prod_id, qty, unit_price, discount))

        cursor.execute(
            "INSERT INTO orders (customer_id, order_date, status, total_amount, shipping_address, payment_method) VALUES (?,?,?,?,?,?)",
            (cust_id, order_date.isoformat(), status, round(total, 2), f"{random.randint(1,999)} Main St", payment)
        )
        order_id = cursor.lastrowid
        for prod_id, qty, unit_price, discount in items:
            cursor.execute(
                "INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount) VALUES (?,?,?,?,?)",
                (order_id, prod_id, qty, unit_price, discount)
            )

    for prod_id in range(1, 26):
        reviewers = random.sample(range(1, 61), random.randint(2, 8))
        for cust_id in reviewers:
            rating = random.choices([1,2,3,4,5], weights=[5,10,15,35,35])[0]
            titles = ['Great product!','Not bad','Excellent quality','Disappointed','Worth every penny',
                      'Good value','Average','Love it!','Could be better','Amazing!']
            cursor.execute(
                "INSERT INTO reviews (product_id, customer_id, rating, title, comment, created_at) VALUES (?,?,?,?,?,?)",
                (prod_id, cust_id, rating, random.choice(titles),
                 f"{'Highly recommend!' if rating >= 4 else 'It was okay.' if rating == 3 else 'Not satisfied.'}",
                 (datetime(2023, 8, 1) + timedelta(days=random.randint(0, 500))).isoformat())
            )

    warehouses = ['Warehouse-A', 'Warehouse-B', 'Warehouse-C']
    for prod_id in range(1, 26):
        cursor.execute(
            "INSERT INTO inventory (product_id, quantity_in_stock, reorder_level, warehouse_location, last_restocked) VALUES (?,?,?,?,?)",
            (prod_id, random.randint(0, 200), random.randint(5, 25),
             random.choice(warehouses),
             (datetime(2024, 1, 1) + timedelta(days=random.randint(0, 300))).isoformat())
        )

    conn.commit()
    conn.close()
    print(f"✅ Database created at {DB_PATH}")
    print(f"   Tables: categories, products, customers, orders, order_items, reviews, inventory")

if __name__ == "__main__":
    create_database()
