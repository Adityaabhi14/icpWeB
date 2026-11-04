import os
import tempfile
import unittest
import io
from app import create_app
import database
from models import (
    UserModel, ExpenseModel, CategoryModel,
    SubscriptionModel, CategoryBudgetModel, FinancialInsightsModel
)

class PersonalExpensesTrackerTestCase(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.temp_upload_dir = tempfile.mkdtemp()
        self.app = create_app({
            'TESTING': True,
            'DATABASE': self.db_path,
            'UPLOAD_FOLDER': self.temp_upload_dir,
            'SECRET_KEY': 'test-key-expenses',
            'WTF_CSRF_ENABLED': False
        })
        self.client = self.app.test_client()

        with self.app.app_context():
            database.init_db()

    def tearDown(self):
        os.close(self.db_fd)
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
        for f in os.listdir(self.temp_upload_dir):
            os.unlink(os.path.join(self.temp_upload_dir, f))
        os.rmdir(self.temp_upload_dir)

    def test_database_initialization(self):
        """Ensure schema is created and default categories (expense + income) are seeded."""
        with self.app.app_context():
            categories = CategoryModel.get_all()
            self.assertGreater(len(categories), 8)
            names = [c['name'] for c in categories]
            self.assertIn('Food & Dining', names)
            self.assertIn('Salary & Wages', names)

    def test_user_registration_and_login(self):
        """Test user account creation and login workflow."""
        response = self.client.post('/register', data={
            'username': 'john_doe',
            'email': 'john@example.com',
            'password': 'password123',
            'confirm_password': 'password123',
            'monthly_budget': '3000.0',
            'currency': '$'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        with self.app.app_context():
            user = UserModel.get_by_username('john_doe')
            self.assertIsNotNone(user)
            self.assertEqual(user['email'], 'john@example.com')
            self.assertEqual(user['monthly_budget'], 3000.0)

        # Logout
        self.client.get('/logout', follow_redirects=True)

        # Login with correct credentials
        response = self.client.post('/login', data={
            'identifier': 'john_doe',
            'password': 'password123'
        }, follow_redirects=True)
        self.assertIn(b'Welcome back, john_doe!', response.data)

    def test_income_and_expense_cashflow(self):
        """Test recording both income and expense and verifying net savings."""
        with self.app.app_context():
            user_id = UserModel.create('cashflow_user', 'cash@example.com', 'password123')

            # Record Income
            ExpenseModel.create(
                user_id=user_id,
                category_id=None,
                title='Consulting Pay',
                amount=5000.0,
                date='2026-11-01',
                exp_type='income'
            )

            # Record Expense
            ExpenseModel.create(
                user_id=user_id,
                category_id=None,
                title='MacBook Purchase',
                amount=2000.0,
                date='2026-11-02',
                exp_type='expense'
            )

            stats = ExpenseModel.get_summary_stats(user_id, month=11, year=2026)
            self.assertEqual(stats['month_income'], 5000.0)
            self.assertEqual(stats['month_total'], 2000.0)
            self.assertEqual(stats['net_savings'], 3000.0)
            self.assertEqual(stats['savings_rate'], 60.0)

    def test_subscription_lifecycle(self):
        """Test creating subscription, pausing/resuming, and recording payment."""
        with self.app.app_context():
            user_id = UserModel.create('sub_user', 'sub@example.com', 'password123')

            # Create subscription
            sub_id = SubscriptionModel.create(
                user_id=user_id,
                category_id=None,
                title='Netflix 4K',
                amount=20.0,
                billing_cycle='Monthly',
                next_due_date='2026-11-10'
            )
            self.assertIsNotNone(sub_id)

            sub = SubscriptionModel.get_by_id(sub_id, user_id)
            self.assertEqual(sub['title'], 'Netflix 4K')
            self.assertEqual(sub['status'], 'Active')

            # Toggle status to paused
            new_status = SubscriptionModel.toggle_status(sub_id, user_id)
            self.assertEqual(new_status, 'Paused')

            # Toggle back to active
            new_status = SubscriptionModel.toggle_status(sub_id, user_id)
            self.assertEqual(new_status, 'Active')

            # Record payment
            exp_id = SubscriptionModel.record_payment(sub_id, user_id)
            self.assertIsNotNone(exp_id)

            # Check expense was recorded
            exp = ExpenseModel.get_by_id(exp_id, user_id)
            self.assertIn('Netflix 4K', exp['title'])
            self.assertEqual(exp['amount'], 20.0)

    def test_category_budget_allocation(self):
        """Test setting individual category budgets and tracking percentage spent."""
        with self.app.app_context():
            user_id = UserModel.create('budget_user', 'budget@example.com', 'password123')
            categories = CategoryModel.get_all(user_id, cat_type='expense')
            food_cat = [c for c in categories if c['name'] == 'Food & Dining'][0]

            # Set Food & Dining budget to $500
            CategoryBudgetModel.set_budget(user_id, food_cat['id'], 500.0)

            # Spend $250 on dining
            ExpenseModel.create(
                user_id=user_id,
                category_id=food_cat['id'],
                title='Steakhouse',
                amount=250.0,
                date='2026-11-03',
                exp_type='expense'
            )

            budgets = CategoryBudgetModel.get_all_with_spent(user_id, month=11, year=2026)
            food_budget = [b for b in budgets if b['category_id'] == food_cat['id']][0]
            self.assertEqual(food_budget['budget'], 500.0)
            self.assertEqual(food_budget['spent'], 250.0)
            self.assertEqual(food_budget['percent'], 50.0)

    def test_financial_health_score(self):
        """Test health score algorithm and insights generator."""
        with self.app.app_context():
            user_id = UserModel.create('health_user', 'health@example.com', 'password123', monthly_budget=3000.0)

            # Give user income and controlled expense
            ExpenseModel.create(user_id, None, 'Salary', 6000.0, '2026-11-01', exp_type='income')
            ExpenseModel.create(user_id, None, 'Rent', 1200.0, '2026-11-02', exp_type='expense')

            health = FinancialInsightsModel.generate_health_score_and_insights(user_id, month=11, year=2026)
            self.assertGreaterEqual(health['score'], 70)
            self.assertIn(health['label'], ['Good', 'Excellent'])
            self.assertGreater(len(health['insights']), 0)

    def test_csv_import(self):
        """Test importing transactions from a CSV file."""
        self.client.post('/register', data={
            'username': 'importer',
            'email': 'importer@example.com',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)

        csv_content = (
            "Date,Title,Amount,Category,Type,Payment Method,Notes\n"
            "2026-11-01,Client Retainer,1500.00,Freelance & Consulting,income,Bank Transfer,Monthly fee\n"
            "2026-11-02,Office Supplies,75.20,Shopping,expense,Credit Card,Pens and notebooks\n"
        )
        data = {
            'csv_file': (io.BytesIO(csv_content.encode('utf-8')), 'statement.csv')
        }
        response = self.client.post('/expenses/import', data=data, content_type='multipart/form-data', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Successfully imported 2 transactions', response.data)

if __name__ == '__main__':
    unittest.main()
