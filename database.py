import sqlite3
import os
from flask import g, current_app

DEFAULT_CATEGORIES = [
    # Expense categories
    ('Food & Dining', 'expense', 'fas fa-utensils', '#EF4444'),
    ('Groceries', 'expense', 'fas fa-shopping-basket', '#F97316'),
    ('Transportation', 'expense', 'fas fa-car', '#F59E0B'),
    ('Housing & Rent', 'expense', 'fas fa-home', '#10B981'),
    ('Utilities & Bills', 'expense', 'fas fa-bolt', '#06B6D4'),
    ('Entertainment', 'expense', 'fas fa-film', '#6366F1'),
    ('Health & Fitness', 'expense', 'fas fa-heartbeat', '#EC4899'),
    ('Shopping', 'expense', 'fas fa-shopping-bag', '#8B5CF6'),
    ('Education & Learning', 'expense', 'fas fa-graduation-cap', '#3B82F6'),
    ('Personal Care', 'expense', 'fas fa-spa', '#14B8A6'),
    ('Miscellaneous', 'expense', 'fas fa-layer-group', '#64748B'),
    # Income categories
    ('Salary & Wages', 'income', 'fas fa-money-bill-wave', '#10B981'),
    ('Freelance & Consulting', 'income', 'fas fa-laptop-code', '#3B82F6'),
    ('Investments & Dividends', 'income', 'fas fa-chart-line', '#8B5CF6'),
    ('Side Hustle & Business', 'income', 'fas fa-briefcase', '#F59E0B'),
    ('Gifts & Other Income', 'income', 'fas fa-gift', '#06B6D4')
]

def get_db():
    """Opens a new database connection if there is none yet for the current application context."""
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON;")
    return g.db

def close_db(e=None):
    """Closes the database again at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def auto_migrate_schema(db):
    """Automatically applies additive schema updates (new columns, new tables) safely."""
    cursor = db.cursor()

    # If expenses table already exists from an older version, add missing columns before creating indexes
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='expenses'")
    if cursor.fetchone():
        cursor.execute("PRAGMA table_info(expenses)")
        columns = [col['name'] for col in cursor.fetchall()]
        if 'type' not in columns:
            cursor.execute("ALTER TABLE expenses ADD COLUMN type TEXT NOT NULL DEFAULT 'expense'")
        if 'receipt_filename' not in columns:
            cursor.execute("ALTER TABLE expenses ADD COLUMN receipt_filename TEXT")

    # If categories table already exists, check type column
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='categories'")
    if cursor.fetchone():
        cursor.execute("PRAGMA table_info(categories)")
        cat_cols = [col['name'] for col in cursor.fetchall()]
        if 'type' not in cat_cols:
            cursor.execute("ALTER TABLE categories ADD COLUMN type TEXT NOT NULL DEFAULT 'expense'")

    db.commit()

    # Now execute full schema script (creates any missing tables like subscriptions, category_budgets, and indexes)
    with current_app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())

    db.commit()

def seed_default_categories(db):
    """Ensure baseline default categories exist."""
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM categories WHERE user_id IS NULL")
    count = cursor.fetchone()['count']
    if count == 0:
        cursor.executemany(
            "INSERT INTO categories (user_id, name, type, icon, color) VALUES (NULL, ?, ?, ?, ?)",
            DEFAULT_CATEGORIES
        )
        db.commit()
    else:
        # Check if income categories are present, if not add them
        cursor.execute("SELECT COUNT(*) as count FROM categories WHERE user_id IS NULL AND type = 'income'")
        inc_count = cursor.fetchone()['count']
        if inc_count == 0:
            income_cats = [c for c in DEFAULT_CATEGORIES if c[1] == 'income']
            cursor.executemany(
                "INSERT INTO categories (user_id, name, type, icon, color) VALUES (NULL, ?, ?, ?, ?)",
                income_cats
            )
            db.commit()

def init_db(app=None):
    """Initializes the database using schema.sql and seeds default categories."""
    if app:
        with app.app_context():
            db = get_db()
            auto_migrate_schema(db)
            seed_default_categories(db)
            db.commit()
    else:
        db = get_db()
        auto_migrate_schema(db)
        seed_default_categories(db)
        db.commit()

def init_app(app):
    """Register database functions with the Flask app."""
    app.teardown_appcontext(close_db)
    os.makedirs(app.config.get('UPLOAD_FOLDER', os.path.join(app.root_path, 'static', 'uploads', 'receipts')), exist_ok=True)
