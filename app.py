import os
from flask import Flask, render_template
from config import Config
import database

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)

    if test_config is not None:
        app.config.update(test_config)

    # Initialize SQLite database handling
    database.init_app(app)

    # Automatically create tables & migrate schema if needed
    db_path = app.config['DATABASE']
    with app.app_context():
        database.init_db()

    # Register blueprints
    from auth import auth_bp
    from expenses import expenses_bp
    from analytics import analytics_bp
    from subscriptions import subscriptions_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(subscriptions_bp)

    # Custom Jinja template filters
    @app.template_filter('currency')
    def currency_filter(value, symbol='$'):
        try:
            return f"{symbol}{float(value):,.2f}"
        except (ValueError, TypeError):
            return f"{symbol}0.00"

    @app.template_filter('format_date')
    def format_date_filter(date_str):
        try:
            from datetime import datetime
            dt = datetime.strptime(str(date_str), '%Y-%m-%d')
            return dt.strftime('%b %d, %Y')
        except Exception:
            return date_str

    # Custom error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template('500.html'), 500

    return app

if __name__ == '__main__':
    app = create_app()
    print("==================================================================")
    print(" SpendWise - Personal Expenses & Cashflow Tracker is starting...")
    print(" Access the application at http://127.0.0.1:5000")
    print("==================================================================")
    app.run(debug=True, host='127.0.0.1', port=5000)
