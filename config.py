import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-expenses-tracker-2026!#@$')
    DATABASE = os.environ.get('DATABASE_PATH', os.path.join(BASE_DIR, 'expenses.db'))
    ITEMS_PER_PAGE = 10
    DEFAULT_CURRENCY = '$'
    DEFAULT_MONTHLY_BUDGET = 2500.0
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads', 'receipts')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'pdf'}
