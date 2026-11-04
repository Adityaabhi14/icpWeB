-- Personal Expenses Tracker Database Schema
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    monthly_budget REAL DEFAULT 2500.0,
    currency TEXT DEFAULT '$',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER, -- NULL for default system categories, or user_id for custom categories
    name TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'expense', -- 'expense' or 'income'
    icon TEXT DEFAULT 'fas fa-tag',
    color TEXT DEFAULT '#4F46E5',
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    category_id INTEGER,
    title TEXT NOT NULL,
    amount REAL NOT NULL CHECK(amount > 0),
    type TEXT NOT NULL DEFAULT 'expense', -- 'expense' or 'income'
    date TEXT NOT NULL, -- Format YYYY-MM-DD
    payment_method TEXT NOT NULL DEFAULT 'Credit Card',
    receipt_filename TEXT,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    category_id INTEGER,
    title TEXT NOT NULL,
    amount REAL NOT NULL CHECK(amount > 0),
    billing_cycle TEXT NOT NULL DEFAULT 'Monthly', -- 'Monthly', 'Yearly', 'Weekly'
    next_due_date TEXT NOT NULL, -- Format YYYY-MM-DD
    payment_method TEXT NOT NULL DEFAULT 'Credit Card',
    status TEXT NOT NULL DEFAULT 'Active', -- 'Active', 'Paused'
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS category_budgets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    budget_amount REAL NOT NULL CHECK(budget_amount >= 0),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE CASCADE,
    UNIQUE(user_id, category_id)
);

CREATE INDEX IF NOT EXISTS idx_expenses_user_date ON expenses (user_id, date);
CREATE INDEX IF NOT EXISTS idx_expenses_user_type_date ON expenses (user_id, type, date);
CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses (category_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions (user_id, next_due_date);
