import functools
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, g
from models import UserModel, ExpenseModel

auth_bp = Blueprint('auth', __name__)

def login_required(view):
    """View decorator that redirects anonymous users to the login page."""
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return view(**kwargs)
    return wrapped_view

@auth_bp.before_app_request
def load_logged_in_user():
    """If a user id is stored in the session, load the user object from the database into ``g.user``."""
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        g.user = UserModel.get_by_id(user_id)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if g.user:
        return redirect(url_for('analytics.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        monthly_budget = request.form.get('monthly_budget', '2500.0')
        currency = request.form.get('currency', '$')

        error = None
        if not username or len(username) < 3:
            error = 'Username must be at least 3 characters long.'
        elif not email or '@' not in email:
            error = 'Please provide a valid email address.'
        elif not password or len(password) < 6:
            error = 'Password must be at least 6 characters long.'
        elif password != confirm_password:
            error = 'Passwords do not match.'
        elif UserModel.get_by_username(username):
            error = f'Username "{username}" is already taken.'
        elif UserModel.get_by_email(email):
            error = f'Email "{email}" is already registered.'

        if error is None:
            try:
                budget_val = float(monthly_budget) if monthly_budget else 2500.0
                user_id = UserModel.create(username, email, password, budget_val, currency)
                # Auto-seed sample demo expenses for a delightful immediate experience
                ExpenseModel.seed_demo_data(user_id)
                session.clear()
                session['user_id'] = user_id
                flash(f'Welcome, {username}! Your account has been created with demo transactions loaded.', 'success')
                return redirect(url_for('analytics.dashboard'))
            except Exception as e:
                error = f'Registration failed: {str(e)}'

        flash(error, 'danger')

    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if g.user:
        return redirect(url_for('analytics.dashboard'))

    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password', '')
        error = None

        if not identifier or not password:
            error = 'Please provide both username/email and password.'
        else:
            user = UserModel.get_by_username(identifier) or UserModel.get_by_email(identifier)
            if user is None or not UserModel.verify_password(user['password_hash'], password):
                error = 'Invalid credentials. Please verify and try again.'

        if error is None:
            session.clear()
            session['user_id'] = user['id']
            flash(f'Welcome back, {user["username"]}!', 'success')
            next_url = request.args.get('next')
            return redirect(next_url or url_for('analytics.dashboard'))

        flash(error, 'danger')

    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_settings':
            monthly_budget = request.form.get('monthly_budget', '2500.0')
            currency = request.form.get('currency', '$')
            try:
                budget_val = max(0.0, float(monthly_budget))
                UserModel.update_budget(g.user['id'], budget_val, currency)
                flash('Budget and currency settings updated successfully!', 'success')
            except ValueError:
                flash('Please enter a valid numeric monthly budget.', 'danger')

        elif action == 'change_password':
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')

            if not UserModel.verify_password(g.user['password_hash'], current_password):
                flash('Current password is incorrect.', 'danger')
            elif len(new_password) < 6:
                flash('New password must be at least 6 characters long.', 'danger')
            elif new_password != confirm_password:
                flash('New passwords do not match.', 'danger')
            else:
                UserModel.change_password(g.user['id'], new_password)
                flash('Password updated successfully!', 'success')

        return redirect(url_for('auth.profile'))

    return render_template('profile.html', user=g.user)

@auth_bp.route('/demo-seed', methods=['POST'])
@login_required
def demo_seed():
    """Manually load realistic demo data for testing."""
    count = ExpenseModel.seed_demo_data(g.user['id'])
    if count > 0:
        flash(f'Successfully seeded {count} demo expense transactions!', 'success')
    else:
        flash('You already have expenses! Delete existing ones first if you wish to reset demo data.', 'info')
    return redirect(url_for('analytics.dashboard'))

