from datetime import datetime, timedelta
import csv
import io
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db

class UserModel:
    @staticmethod
    def create(username, email, password, monthly_budget=2500.0, currency='$'):
        db = get_db()
        password_hash = generate_password_hash(password)
        try:
            cursor = db.execute(
                "INSERT INTO users (username, email, password_hash, monthly_budget, currency) VALUES (?, ?, ?, ?, ?)",
                (username.strip(), email.strip().lower(), password_hash, float(monthly_budget), currency)
            )
            db.commit()
            return cursor.lastrowid
        except Exception as e:
            db.rollback()
            raise e

    @staticmethod
    def get_by_id(user_id):
        db = get_db()
        return db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

    @staticmethod
    def get_by_username(username):
        db = get_db()
        return db.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(?)", (username.strip(),)).fetchone()

    @staticmethod
    def get_by_email(email):
        db = get_db()
        return db.execute("SELECT * FROM users WHERE LOWER(email) = LOWER(?)", (email.strip(),)).fetchone()

    @staticmethod
    def update_budget(user_id, monthly_budget, currency='$'):
        db = get_db()
        db.execute(
            "UPDATE users SET monthly_budget = ?, currency = ? WHERE id = ?",
            (float(monthly_budget), currency, user_id)
        )
        db.commit()

    @staticmethod
    def change_password(user_id, new_password):
        db = get_db()
        password_hash = generate_password_hash(new_password)
        db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id))
        db.commit()

    @staticmethod
    def verify_password(stored_hash, candidate_password):
        return check_password_hash(stored_hash, candidate_password)


class CategoryModel:
    @staticmethod
    def get_all(user_id=None, cat_type=None):
        db = get_db()
        query = "SELECT * FROM categories WHERE (user_id IS NULL"
        params = []
        if user_id:
            query += " OR user_id = ?)"
            params.append(user_id)
        else:
            query += ")"

        if cat_type:
            query += " AND type = ?"
            params.append(cat_type)

        query += " ORDER BY type DESC, name ASC"
        return db.execute(query, params).fetchall()

    @staticmethod
    def get_by_id(category_id, user_id=None):
        db = get_db()
        if user_id:
            return db.execute(
                "SELECT * FROM categories WHERE id = ? AND (user_id IS NULL OR user_id = ?)",
                (category_id, user_id)
            ).fetchone()
        return db.execute("SELECT * FROM categories WHERE id = ?", (category_id,)).fetchone()

    @staticmethod
    def create(user_id, name, cat_type='expense', icon='fas fa-tag', color='#4F46E5'):
        db = get_db()
        cursor = db.execute(
            "INSERT INTO categories (user_id, name, type, icon, color) VALUES (?, ?, ?, ?, ?)",
            (user_id, name.strip(), cat_type, icon, color)
        )
        db.commit()
        return cursor.lastrowid

    @staticmethod
    def delete(category_id, user_id):
        db = get_db()
        cursor = db.execute(
            "DELETE FROM categories WHERE id = ? AND user_id = ?",
            (category_id, user_id)
        )
        db.commit()
        return cursor.rowcount > 0


class CategoryBudgetModel:
    @staticmethod
    def set_budget(user_id, category_id, budget_amount):
        db = get_db()
        db.execute(
            """INSERT INTO category_budgets (user_id, category_id, budget_amount)
               VALUES (?, ?, ?)
               ON CONFLICT(user_id, category_id)
               DO UPDATE SET budget_amount = excluded.budget_amount""",
            (user_id, category_id, max(0.0, float(budget_amount)))
        )
        db.commit()

    @staticmethod
    def get_all_with_spent(user_id, month=None, year=None):
        db = get_db()
        now = datetime.now()
        month = month or now.month
        year = year or now.year
        month_str = f"{year:04d}-{month:02d}"

        rows = db.execute(
            """SELECT c.id as category_id, c.name, c.icon, c.color,
                      COALESCE(cb.budget_amount, 0.0) as budget_amount,
                      COALESCE(spent_tbl.total_spent, 0.0) as spent
               FROM categories c
               LEFT JOIN category_budgets cb ON c.id = cb.category_id AND cb.user_id = ?
               LEFT JOIN (
                   SELECT category_id, SUM(amount) as total_spent
                   FROM expenses
                   WHERE user_id = ? AND type = 'expense' AND strftime('%Y-%m', date) = ?
                   GROUP BY category_id
               ) spent_tbl ON c.id = spent_tbl.category_id
               WHERE (c.user_id IS NULL OR c.user_id = ?) AND c.type = 'expense'
               ORDER BY budget_amount DESC, spent DESC""",
            (user_id, user_id, month_str, user_id)
        ).fetchall()

        results = []
        for r in rows:
            budget = round(r['budget_amount'], 2)
            spent = round(r['spent'], 2)
            pct = min(100.0, round((spent / budget * 100), 1)) if budget > 0 else 0.0
            results.append({
                'category_id': r['category_id'],
                'name': r['name'],
                'icon': r['icon'],
                'color': r['color'],
                'budget': budget,
                'spent': spent,
                'remaining': round(max(0.0, budget - spent), 2),
                'percent': pct,
                'has_budget': budget > 0
            })
        return results


class ExpenseModel:
    @staticmethod
    def create(user_id, category_id, title, amount, date, payment_method='Credit Card', notes='', exp_type='expense', receipt_filename=None):
        db = get_db()
        cursor = db.execute(
            """INSERT INTO expenses (user_id, category_id, title, amount, date, payment_method, notes, type, receipt_filename)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, category_id, title.strip(), float(amount), date, payment_method, notes.strip(), exp_type, receipt_filename)
        )
        db.commit()
        return cursor.lastrowid

    @staticmethod
    def get_by_id(expense_id, user_id):
        db = get_db()
        return db.execute(
            """SELECT e.*, c.name as category_name, c.icon as category_icon, c.color as category_color
               FROM expenses e
               LEFT JOIN categories c ON e.category_id = c.id
               WHERE e.id = ? AND e.user_id = ?""",
            (expense_id, user_id)
        ).fetchone()

    @staticmethod
    def update(expense_id, user_id, category_id, title, amount, date, payment_method, notes, exp_type='expense', receipt_filename=None):
        db = get_db()
        if receipt_filename:
            cursor = db.execute(
                """UPDATE expenses
                   SET category_id = ?, title = ?, amount = ?, date = ?, payment_method = ?, notes = ?, type = ?, receipt_filename = ?
                   WHERE id = ? AND user_id = ?""",
                (category_id, title.strip(), float(amount), date, payment_method, notes.strip(), exp_type, receipt_filename, expense_id, user_id)
            )
        else:
            cursor = db.execute(
                """UPDATE expenses
                   SET category_id = ?, title = ?, amount = ?, date = ?, payment_method = ?, notes = ?, type = ?
                   WHERE id = ? AND user_id = ?""",
                (category_id, title.strip(), float(amount), date, payment_method, notes.strip(), exp_type, expense_id, user_id)
            )
        db.commit()
        return cursor.rowcount > 0

    @staticmethod
    def delete(expense_id, user_id):
        db = get_db()
        cursor = db.execute(
            "DELETE FROM expenses WHERE id = ? AND user_id = ?",
            (expense_id, user_id)
        )
        db.commit()
        return cursor.rowcount > 0

    @staticmethod
    def filter_expenses(user_id, start_date=None, end_date=None, category_id=None,
                        payment_method=None, search=None, exp_type=None, limit=10, offset=0):
        db = get_db()
        query = """
            SELECT e.*, c.name as category_name, c.icon as category_icon, c.color as category_color
            FROM expenses e
            LEFT JOIN categories c ON e.category_id = c.id
            WHERE e.user_id = ?
        """
        params = [user_id]

        if exp_type:
            query += " AND e.type = ?"
            params.append(exp_type)
        if start_date:
            query += " AND e.date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND e.date <= ?"
            params.append(end_date)
        if category_id:
            query += " AND e.category_id = ?"
            params.append(category_id)
        if payment_method:
            query += " AND e.payment_method = ?"
            params.append(payment_method)
        if search:
            query += " AND (e.title LIKE ? OR e.notes LIKE ?)"
            term = f"%{search.strip()}%"
            params.extend([term, term])

        query += " ORDER BY e.date DESC, e.id DESC"
        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])

        return db.execute(query, params).fetchall()

    @staticmethod
    def count_expenses(user_id, start_date=None, end_date=None, category_id=None,
                       payment_method=None, search=None, exp_type=None):
        db = get_db()
        query = "SELECT COUNT(*) as count FROM expenses WHERE user_id = ?"
        params = [user_id]

        if exp_type:
            query += " AND type = ?"
            params.append(exp_type)
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        if category_id:
            query += " AND category_id = ?"
            params.append(category_id)
        if payment_method:
            query += " AND payment_method = ?"
            params.append(payment_method)
        if search:
            query += " AND (title LIKE ? OR notes LIKE ?)"
            term = f"%{search.strip()}%"
            params.extend([term, term])

        row = db.execute(query, params).fetchone()
        return row['count'] if row else 0

    @staticmethod
    def get_summary_stats(user_id, month=None, year=None):
        db = get_db()
        now = datetime.now()
        month = month or now.month
        year = year or now.year
        month_str = f"{year:04d}-{month:02d}"

        # Current month expenses
        exp_row = db.execute(
            """SELECT COALESCE(SUM(amount), 0.0) as total, COUNT(*) as count,
                      COALESCE(AVG(amount), 0.0) as avg_amount
               FROM expenses
               WHERE user_id = ? AND type = 'expense' AND strftime('%Y-%m', date) = ?""",
            (user_id, month_str)
        ).fetchone()

        # Current month income
        inc_row = db.execute(
            """SELECT COALESCE(SUM(amount), 0.0) as total, COUNT(*) as count
               FROM expenses
               WHERE user_id = ? AND type = 'income' AND strftime('%Y-%m', date) = ?""",
            (user_id, month_str)
        ).fetchone()

        # All-time totals
        all_exp = db.execute(
            "SELECT COALESCE(SUM(amount), 0.0) as total, COUNT(*) as count FROM expenses WHERE user_id = ? AND type = 'expense'",
            (user_id,)
        ).fetchone()

        all_inc = db.execute(
            "SELECT COALESCE(SUM(amount), 0.0) as total FROM expenses WHERE user_id = ? AND type = 'income'",
            (user_id,)
        ).fetchone()

        # Top category this month
        top_cat_row = db.execute(
            """SELECT c.name, SUM(e.amount) as total
               FROM expenses e
               LEFT JOIN categories c ON e.category_id = c.id
               WHERE e.user_id = ? AND e.type = 'expense' AND strftime('%Y-%m', e.date) = ?
               GROUP BY e.category_id
               ORDER BY total DESC
               LIMIT 1""",
            (user_id, month_str)
        ).fetchone()

        exp_total = round(exp_row['total'], 2)
        inc_total = round(inc_row['total'], 2)
        net_savings = round(inc_total - exp_total, 2)
        savings_rate = round((net_savings / inc_total * 100), 1) if inc_total > 0 else 0.0

        return {
            'month_total': exp_total,
            'month_income': inc_total,
            'net_savings': net_savings,
            'savings_rate': savings_rate,
            'month_count': exp_row['count'],
            'month_avg': round(exp_row['avg_amount'], 2),
            'all_time_total': round(all_exp['total'], 2),
            'all_time_income': round(all_inc['total'], 2),
            'all_time_count': all_exp['count'],
            'top_category': top_cat_row['name'] if top_cat_row else 'None',
            'top_category_amount': round(top_cat_row['total'], 2) if top_cat_row else 0.0,
            'selected_month': month_str
        }

    @staticmethod
    def get_category_breakdown(user_id, month=None, year=None, exp_type='expense'):
        db = get_db()
        now = datetime.now()
        month = month or now.month
        year = year or now.year
        month_str = f"{year:04d}-{month:02d}"

        rows = db.execute(
            """SELECT COALESCE(c.name, 'Uncategorized') as category,
                      COALESCE(c.color, '#64748B') as color,
                      COALESCE(c.icon, 'fas fa-tag') as icon,
                      SUM(e.amount) as total,
                      COUNT(e.id) as count
               FROM expenses e
               LEFT JOIN categories c ON e.category_id = c.id
               WHERE e.user_id = ? AND e.type = ? AND strftime('%Y-%m', e.date) = ?
               GROUP BY e.category_id
               ORDER BY total DESC""",
            (user_id, exp_type, month_str)
        ).fetchall()

        return [
            {
                'category': r['category'],
                'color': r['color'],
                'icon': r['icon'],
                'total': round(r['total'], 2),
                'count': r['count']
            }
            for r in rows
        ]

    @staticmethod
    def get_monthly_trends(user_id, months=6):
        """Returns expenses, income, and net savings for the last `months` months."""
        db = get_db()
        now = datetime.now()
        results = []

        for i in range(months - 1, -1, -1):
            cur_month = now.month - i
            cur_year = now.year
            while cur_month <= 0:
                cur_month += 12
                cur_year -= 1

            month_key = f"{cur_year:04d}-{cur_month:02d}"
            month_label = datetime(cur_year, cur_month, 1).strftime("%b %Y")

            exp_row = db.execute(
                """SELECT COALESCE(SUM(amount), 0.0) as total
                   FROM expenses
                   WHERE user_id = ? AND type = 'expense' AND strftime('%Y-%m', date) = ?""",
                (user_id, month_key)
            ).fetchone()

            inc_row = db.execute(
                """SELECT COALESCE(SUM(amount), 0.0) as total
                   FROM expenses
                   WHERE user_id = ? AND type = 'income' AND strftime('%Y-%m', date) = ?""",
                (user_id, month_key)
            ).fetchone()

            exp = round(exp_row['total'], 2)
            inc = round(inc_row['total'], 2)

            results.append({
                'month_key': month_key,
                'label': month_label,
                'expenses': exp,
                'income': inc,
                'net_savings': round(inc - exp, 2)
            })

        return results

    @staticmethod
    def get_payment_method_breakdown(user_id, month=None, year=None):
        db = get_db()
        now = datetime.now()
        month = month or now.month
        year = year or now.year
        month_str = f"{year:04d}-{month:02d}"

        rows = db.execute(
            """SELECT payment_method, SUM(amount) as total, COUNT(*) as count
               FROM expenses
               WHERE user_id = ? AND strftime('%Y-%m', date) = ?
               GROUP BY payment_method
               ORDER BY total DESC""",
            (user_id, month_str)
        ).fetchall()

        return [
            {'method': r['payment_method'], 'total': round(r['total'], 2), 'count': r['count']}
            for r in rows
        ]

    @staticmethod
    def bulk_import_csv(user_id, file_stream):
        """Imports expenses from a CSV file stream. Returns count of imported rows."""
        db = get_db()
        content = file_stream.read().decode('utf-8', errors='ignore')
        reader = csv.DictReader(io.StringIO(content))

        # Build category cache
        categories = db.execute("SELECT id, name, type FROM categories WHERE user_id IS NULL OR user_id = ?", (user_id,)).fetchall()
        cat_map = {c['name'].strip().lower(): c['id'] for c in categories}

        inserted = 0
        for row in reader:
            # Flexible column headers
            title = row.get('Title') or row.get('title') or row.get('Description') or row.get('description') or 'Imported Item'
            amount_val = row.get('Amount') or row.get('amount') or 0.0
            date_val = row.get('Date') or row.get('date') or datetime.now().strftime("%Y-%m-%d")
            cat_name = (row.get('Category') or row.get('category') or 'Miscellaneous').strip()
            pm = row.get('Payment Method') or row.get('payment_method') or 'Credit Card'
            notes = row.get('Notes') or row.get('notes') or ''
            exp_type = (row.get('Type') or row.get('type') or 'expense').strip().lower()
            if exp_type not in ('expense', 'income'):
                exp_type = 'expense'

            try:
                amount = float(amount_val)
                if amount <= 0:
                    continue
            except (ValueError, TypeError):
                continue

            # Resolve category or create if missing
            cat_id = cat_map.get(cat_name.lower())
            if not cat_id:
                cursor = db.execute(
                    "INSERT INTO categories (user_id, name, type, icon, color) VALUES (?, ?, ?, 'fas fa-tag', '#6366F1')",
                    (user_id, cat_name, exp_type)
                )
                cat_id = cursor.lastrowid
                cat_map[cat_name.lower()] = cat_id

            db.execute(
                """INSERT INTO expenses (user_id, category_id, title, amount, date, payment_method, notes, type)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, cat_id, title.strip(), amount, date_val.strip(), pm.strip(), notes.strip(), exp_type)
            )
            inserted += 1

        db.commit()
        return inserted

    @staticmethod
    def seed_demo_data(user_id):
        """Populates realistic demo income, expenses, and subscriptions."""
        db = get_db()
        count = db.execute("SELECT COUNT(*) as c FROM expenses WHERE user_id = ?", (user_id,)).fetchone()['c']
        if count > 0:
            return 0

        categories = db.execute("SELECT id, name, type FROM categories WHERE user_id IS NULL OR user_id = ?", (user_id,)).fetchall()
        cat_map = {c['name']: c['id'] for c in categories}

        now = datetime.now()

        # 1. Seed Income
        incomes = [
            ('Monthly Software Engineering Salary', 4200.00, 'Salary & Wages', 'Bank Transfer', 'Primary payroll deposit', 1),
            ('Freelance UI/UX Dashboard Project', 850.00, 'Freelance & Consulting', 'UPI / Online', 'Direct client payment', 12),
            ('Quarterly ETF Dividends', 125.40, 'Investments & Dividends', 'Bank Transfer', 'Brokerage portfolio dividend', 15),
        ]
        for title, amount, cat, pm, notes, offset in incomes:
            d = (now - timedelta(days=offset)).strftime("%Y-%m-%d")
            db.execute(
                """INSERT INTO expenses (user_id, category_id, title, amount, date, payment_method, notes, type)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'income')""",
                (user_id, cat_map.get(cat), title, amount, d, pm, notes)
            )

        # 2. Seed Expenses
        demo_expenses = [
            ('Apartment Rent', 950.00, 'Housing & Rent', 'Bank Transfer', 'Monthly residential rent', 1),
            ('Weekly Whole Foods Groceries', 112.40, 'Groceries', 'Credit Card', 'Organic fruits, almond milk, salmon', 2),
            ('Dinner with Colleagues', 65.50, 'Food & Dining', 'Credit Card', 'Italian Bistro downtown', 3),
            ('Fiber Internet Bill', 60.00, 'Utilities & Bills', 'UPI / Online', '500mbps home fiber connection', 4),
            ('Gas Station Refill', 52.00, 'Transportation', 'Credit Card', 'Full tank fuel', 5),
            ('Ergonomic Mouse & Desk Mat', 54.99, 'Shopping', 'Credit Card', 'Home office productivity upgrade', 6),
            ('Gym & Fitness Pass', 55.00, 'Health & Fitness', 'Debit Card', 'Monthly gym & pool membership', 7),
            ('Metro Transit Pass Recharge', 45.00, 'Transportation', 'Debit Card', 'Subway & bus monthly pass', 8),
            ('Weekend Cafe & Pastry', 18.50, 'Food & Dining', 'Cash', 'Espresso & almond croissant', 9),
            ('Supermarket Pantry Essentials', 78.90, 'Groceries', 'Debit Card', 'Household goods, olive oil, coffee', 10),
            ('Electricity & Heating Utility', 85.30, 'Utilities & Bills', 'Bank Transfer', 'Monthly power provider invoice', 11),
            ('Pharmacy & Multivitamins', 28.60, 'Health & Fitness', 'Debit Card', 'Omega 3 & vitamins', 12),
            ('IMAX Cinema Tickets & Popcorn', 32.00, 'Entertainment', 'UPI / Online', 'Weekend sci-fi movie night', 13),
            ('Online Tech Course / Python Mastery', 29.99, 'Education & Learning', 'Credit Card', 'Data architecture video course', 14),
            ('Farmers Market Fresh Produce', 24.50, 'Groceries', 'Cash', 'Organic apples, berries & honey', 16),
            ('Mobile Phone Unlimited 5G Plan', 45.00, 'Utilities & Bills', 'Credit Card', 'Unlimited talk, text & data', 18),
        ]
        for title, amount, cat, pm, notes, offset in demo_expenses:
            d = (now - timedelta(days=offset)).strftime("%Y-%m-%d")
            db.execute(
                """INSERT INTO expenses (user_id, category_id, title, amount, date, payment_method, notes, type)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'expense')""",
                (user_id, cat_map.get(cat), title, amount, d, pm, notes)
            )

        # 3. Seed Category Budgets
        default_budgets = [
            ('Housing & Rent', 1000.00),
            ('Groceries', 350.00),
            ('Food & Dining', 200.00),
            ('Utilities & Bills', 250.00),
            ('Transportation', 150.00),
            ('Shopping', 150.00),
            ('Entertainment', 100.00),
            ('Health & Fitness', 100.00)
        ]
        for cat_name, budget_amt in default_budgets:
            if cat_name in cat_map:
                CategoryBudgetModel.set_budget(user_id, cat_map[cat_name], budget_amt)

        # 4. Seed Subscriptions / Recurring Bills
        demo_subs = [
            ('Netflix Premium 4K', 22.99, 'Entertainment', 'Monthly', 'Credit Card', 5),
            ('Spotify Family Subscription', 16.99, 'Entertainment', 'Monthly', 'Credit Card', 8),
            ('Gym & Health Club Pass', 55.00, 'Health & Fitness', 'Monthly', 'Debit Card', 1),
            ('GitHub Copilot Pro', 10.00, 'Education & Learning', 'Monthly', 'Credit Card', 14),
            ('Amazon Prime Membership', 139.00, 'Shopping', 'Yearly', 'Credit Card', 45),
            ('High-Speed Fiber Internet', 60.00, 'Utilities & Bills', 'Monthly', 'UPI / Online', 4)
        ]
        for title, amount, cat, cycle, pm, days_ahead in demo_subs:
            due_date = (now + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
            SubscriptionModel.create(
                user_id=user_id,
                category_id=cat_map.get(cat),
                title=title,
                amount=amount,
                billing_cycle=cycle,
                next_due_date=due_date,
                payment_method=pm,
                notes='Auto-renew active'
            )

        db.commit()
        return len(demo_expenses) + len(incomes)


class SubscriptionModel:
    @staticmethod
    def create(user_id, category_id, title, amount, billing_cycle='Monthly', next_due_date=None, payment_method='Credit Card', notes=''):
        db = get_db()
        if not next_due_date:
            next_due_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        cursor = db.execute(
            """INSERT INTO subscriptions (user_id, category_id, title, amount, billing_cycle, next_due_date, payment_method, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, category_id, title.strip(), float(amount), billing_cycle, next_due_date, payment_method, notes.strip())
        )
        db.commit()
        return cursor.lastrowid

    @staticmethod
    def get_all(user_id):
        db = get_db()
        return db.execute(
            """SELECT s.*, c.name as category_name, c.icon as category_icon, c.color as category_color
               FROM subscriptions s
               LEFT JOIN categories c ON s.category_id = c.id
               WHERE s.user_id = ?
               ORDER BY s.status ASC, s.next_due_date ASC""",
            (user_id,)
        ).fetchall()

    @staticmethod
    def get_by_id(sub_id, user_id):
        db = get_db()
        return db.execute(
            """SELECT s.*, c.name as category_name, c.icon as category_icon, c.color as category_color
               FROM subscriptions s
               LEFT JOIN categories c ON s.category_id = c.id
               WHERE s.id = ? AND s.user_id = ?""",
            (sub_id, user_id)
        ).fetchone()

    @staticmethod
    def update(sub_id, user_id, category_id, title, amount, billing_cycle, next_due_date, payment_method, status, notes):
        db = get_db()
        cursor = db.execute(
            """UPDATE subscriptions
               SET category_id = ?, title = ?, amount = ?, billing_cycle = ?, next_due_date = ?, payment_method = ?, status = ?, notes = ?
               WHERE id = ? AND user_id = ?""",
            (category_id, title.strip(), float(amount), billing_cycle, next_due_date, payment_method, status, notes.strip(), sub_id, user_id)
        )
        db.commit()
        return cursor.rowcount > 0

    @staticmethod
    def delete(sub_id, user_id):
        db = get_db()
        cursor = db.execute("DELETE FROM subscriptions WHERE id = ? AND user_id = ?", (sub_id, user_id))
        db.commit()
        return cursor.rowcount > 0

    @staticmethod
    def toggle_status(sub_id, user_id):
        sub = SubscriptionModel.get_by_id(sub_id, user_id)
        if not sub:
            return False
        new_status = 'Paused' if sub['status'] == 'Active' else 'Active'
        db = get_db()
        db.execute("UPDATE subscriptions SET status = ? WHERE id = ? AND user_id = ?", (new_status, sub_id, user_id))
        db.commit()
        return new_status

    @staticmethod
    def get_summary(user_id):
        subs = SubscriptionModel.get_all(user_id)
        active_subs = [s for s in subs if s['status'] == 'Active']

        # Normalized monthly cost
        monthly_total = 0.0
        for s in active_subs:
            amt = s['amount']
            cycle = s['billing_cycle'].lower()
            if cycle == 'weekly':
                monthly_total += amt * 4.33
            elif cycle == 'yearly' or cycle == 'annual':
                monthly_total += amt / 12.0
            else:
                monthly_total += amt

        # Upcoming bills within next 7 days
        today = datetime.now().date()
        week_later = today + timedelta(days=7)
        upcoming = []
        for s in active_subs:
            try:
                due = datetime.strptime(s['next_due_date'], '%Y-%m-%d').date()
                if today <= due <= week_later:
                    days_left = (due - today).days
                    upcoming.append({
                        'title': s['title'],
                        'amount': s['amount'],
                        'due_date': s['next_due_date'],
                        'days_left': days_left
                    })
            except Exception:
                pass

        return {
            'total_active': len(active_subs),
            'total_paused': len(subs) - len(active_subs),
            'monthly_recurring_burn': round(monthly_total, 2),
            'upcoming_in_7_days': upcoming
        }

    @staticmethod
    def record_payment(sub_id, user_id):
        """Creates an expense record for the subscription and rolls the due date forward."""
        sub = SubscriptionModel.get_by_id(sub_id, user_id)
        if not sub:
            return None

        today_str = datetime.now().strftime("%Y-%m-%d")
        exp_id = ExpenseModel.create(
            user_id=user_id,
            category_id=sub['category_id'],
            title=f"Recurring: {sub['title']}",
            amount=sub['amount'],
            date=today_str,
            payment_method=sub['payment_method'],
            notes=f"Processed from {sub['billing_cycle']} subscription.",
            exp_type='expense'
        )

        # Advance next due date
        try:
            curr_due = datetime.strptime(sub['next_due_date'], '%Y-%m-%d')
            cycle = sub['billing_cycle'].lower()
            if cycle == 'weekly':
                new_due = curr_due + timedelta(days=7)
            elif cycle == 'yearly' or cycle == 'annual':
                new_due = curr_due.replace(year=curr_due.year + 1)
            else:
                # monthly
                month = curr_due.month + 1
                year = curr_due.year
                if month > 12:
                    month = 1
                    year += 1
                day = min(curr_due.day, 28)
                new_due = datetime(year, month, day)

            db = get_db()
            db.execute("UPDATE subscriptions SET next_due_date = ? WHERE id = ?", (new_due.strftime("%Y-%m-%d"), sub_id))
            db.commit()
        except Exception:
            pass

        return exp_id


class FinancialInsightsModel:
    @staticmethod
    def generate_health_score_and_insights(user_id, month=None, year=None):
        stats = ExpenseModel.get_summary_stats(user_id, month, year)
        user = UserModel.get_by_id(user_id)
        sub_summary = SubscriptionModel.get_summary(user_id)

        budget = user['monthly_budget'] or 0.0
        income = stats['month_income']
        expenses = stats['month_total']
        net_savings = stats['net_savings']

        score = 70  # Baseline
        insights = []

        # 1. Savings Rate Analysis
        if income > 0:
            savings_rate = (net_savings / income) * 100
            if savings_rate >= 30:
                score += 15
                insights.append({
                    'type': 'success',
                    'icon': 'fas fa-arrow-trend-up',
                    'title': 'High Savings Rate',
                    'message': f'You are saving {savings_rate:.1f}% of your monthly earnings, exceeding the recommended 20% benchmark!'
                })
            elif savings_rate >= 15:
                score += 5
                insights.append({
                    'type': 'info',
                    'icon': 'fas fa-piggy-bank',
                    'title': 'Healthy Cash Flow',
                    'message': f'You have a positive savings rate of {savings_rate:.1f}%. Keep maintaining control over discretionary spends.'
                })
            elif savings_rate > 0:
                insights.append({
                    'type': 'warning',
                    'icon': 'fas fa-shield',
                    'title': 'Low Margin of Safety',
                    'message': f'Savings rate is {savings_rate:.1f}%. Consider reviewing non-essential spending to build a stronger emergency cushion.'
                })
            else:
                score -= 20
                insights.append({
                    'type': 'danger',
                    'icon': 'fas fa-exclamation-triangle',
                    'title': 'Negative Cash Flow Alert',
                    'message': f'You spent {user["currency"]}{abs(net_savings):,.2f} more than your recorded income this month.'
                })
        else:
            insights.append({
                'type': 'info',
                'icon': 'fas fa-money-bill-wave',
                'title': 'Track Your Incomes',
                'message': 'Record your salary and freelance deposits to unlock comprehensive cash flow and savings rate analysis!'
            })

        # 2. Overall Budget Burn Rate
        if budget > 0:
            burn_pct = (expenses / budget) * 100
            now = datetime.now()
            days_in_month = 30
            days_elapsed = min(now.day, days_in_month)
            expected_burn = (days_elapsed / days_in_month) * 100

            if burn_pct > 100:
                score -= 15
                insights.append({
                    'type': 'danger',
                    'icon': 'fas fa-circle-exclamation',
                    'title': 'Budget Cap Exceeded',
                    'message': f'Expenses have exceeded your monthly target by {user["currency"]}{(expenses - budget):,.2f}.'
                })
            elif burn_pct > expected_burn + 15:
                score -= 5
                insights.append({
                    'type': 'warning',
                    'icon': 'fas fa-fire',
                    'title': 'Accelerated Burn Rate',
                    'message': f'You have used {burn_pct:.0f}% of budget at day {days_elapsed}. Spending is pacing ahead of schedule.'
                })
            elif burn_pct <= expected_burn:
                score += 10
                insights.append({
                    'type': 'success',
                    'icon': 'fas fa-check-circle',
                    'title': 'Budget Disciplined',
                    'message': f'Spending is pacing under target ({burn_pct:.0f}% vs expected {expected_burn:.0f}%).'
                })

        # 3. Recurring Subscriptions Impact
        if sub_summary['monthly_recurring_burn'] > 0:
            rec_burn = sub_summary['monthly_recurring_burn']
            if income > 0 and (rec_burn / income) > 0.15:
                score -= 5
                insights.append({
                    'type': 'warning',
                    'icon': 'fas fa-repeat',
                    'title': 'High Subscription Load',
                    'message': f'Fixed recurring subscriptions consume {user["currency"]}{rec_burn:,.2f}/month. Review unneeded services.'
                })

        # Clamp score between 10 and 100
        score = max(15, min(100, score))

        # Status Label
        if score >= 85:
            badge = ('Excellent', 'emerald')
        elif score >= 70:
            badge = ('Good', 'indigo')
        elif score >= 50:
            badge = ('Fair', 'amber')
        else:
            badge = ('Needs Attention', 'rose')

        return {
            'score': score,
            'label': badge[0],
            'color': badge[1],
            'insights': insights[:4]
        }
