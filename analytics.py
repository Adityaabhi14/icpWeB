from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, jsonify
from auth import login_required
from models import (
    ExpenseModel, CategoryModel, CategoryBudgetModel,
    SubscriptionModel, FinancialInsightsModel
)

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/')
def index():
    if g.user:
        return redirect(url_for('analytics.dashboard'))
    return redirect(url_for('auth.login'))

@analytics_bp.route('/dashboard')
@login_required
def dashboard():
    user_id = g.user['id']
    now = datetime.now()

    # Get optional month/year filter from query args, default to current
    selected_month = request.args.get('month', type=int, default=now.month)
    selected_year = request.args.get('year', type=int, default=now.year)

    stats = ExpenseModel.get_summary_stats(user_id, selected_month, selected_year)
    monthly_budget = g.user['monthly_budget'] or 0.0
    spent = stats['month_total']
    remaining = max(0.0, monthly_budget - spent)
    budget_pct = min(100.0, round((spent / monthly_budget * 100), 1)) if monthly_budget > 0 else 0.0

    recent_expenses = ExpenseModel.filter_expenses(user_id=user_id, limit=6, offset=0)
    categories = CategoryModel.get_all(user_id)
    category_budgets = CategoryBudgetModel.get_all_with_spent(user_id, selected_month, selected_year)

    # Subscriptions summary
    sub_summary = SubscriptionModel.get_summary(user_id)

    # Smart Health Score & Insights
    health = FinancialInsightsModel.generate_health_score_and_insights(user_id, selected_month, selected_year)

    # Available months list for picker (last 12 months)
    available_months = []
    for i in range(12):
        m = now.month - i
        y = now.year
        while m <= 0:
            m += 12
            y -= 1
        dt = datetime(y, m, 1)
        available_months.append({
            'month': m,
            'year': y,
            'label': dt.strftime('%B %Y'),
            'is_selected': (m == selected_month and y == selected_year)
        })

    today = now.strftime("%Y-%m-%d")

    return render_template(
        'dashboard.html',
        stats=stats,
        monthly_budget=monthly_budget,
        remaining_budget=round(remaining, 2),
        budget_pct=budget_pct,
        recent_expenses=recent_expenses,
        categories=categories,
        category_budgets=category_budgets,
        sub_summary=sub_summary,
        health=health,
        available_months=available_months,
        selected_month=selected_month,
        selected_year=selected_year,
        today=today
    )

@analytics_bp.route('/api/chart-data')
@login_required
def chart_data():
    user_id = g.user['id']
    now = datetime.now()
    month = request.args.get('month', type=int, default=now.month)
    year = request.args.get('year', type=int, default=now.year)

    # 1. Category breakdown for doughnut chart
    categories_data = ExpenseModel.get_category_breakdown(user_id, month, year, exp_type='expense')
    cat_labels = [c['category'] for c in categories_data]
    cat_totals = [c['total'] for c in categories_data]
    cat_colors = [c['color'] for c in categories_data]

    # 2. Monthly trend for 6-month comparative bar chart (Expenses & Incomes)
    trend_data = ExpenseModel.get_monthly_trends(user_id, months=6)
    trend_labels = [t['label'] for t in trend_data]
    trend_expenses = [t['expenses'] for t in trend_data]
    trend_income = [t['income'] for t in trend_data]
    trend_savings = [t['net_savings'] for t in trend_data]

    # 3. Payment methods breakdown
    pm_data = ExpenseModel.get_payment_method_breakdown(user_id, month, year)
    pm_labels = [p['method'] for p in pm_data]
    pm_totals = [p['total'] for p in pm_data]

    return jsonify({
        'categories': {
            'labels': cat_labels,
            'totals': cat_totals,
            'colors': cat_colors,
            'items': categories_data
        },
        'trends': {
            'labels': trend_labels,
            'expenses': trend_expenses,
            'income': trend_income,
            'net_savings': trend_savings
        },
        'paymentMethods': {
            'labels': pm_labels,
            'totals': pm_totals
        }
    })

@analytics_bp.route('/categories', methods=['GET', 'POST'])
@login_required
def categories_view():
    user_id = g.user['id']
    now = datetime.now()

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add':
            name = request.form.get('name', '').strip()
            cat_type = request.form.get('type', 'expense').strip()
            color = request.form.get('color', '#4F46E5')
            icon = request.form.get('icon', 'fas fa-tag')

            if not name:
                flash('Category name is required.', 'danger')
            else:
                CategoryModel.create(user_id, name, cat_type, icon, color)
                flash(f'Category "{name}" added successfully!', 'success')

        elif action == 'delete':
            category_id = request.form.get('category_id', type=int)
            if category_id:
                if CategoryModel.delete(category_id, user_id):
                    flash('Custom category deleted.', 'info')
                else:
                    flash('Default system categories cannot be deleted.', 'warning')

        return redirect(url_for('analytics.categories_view'))

    all_categories = CategoryModel.get_all(user_id)
    category_budgets = CategoryBudgetModel.get_all_with_spent(user_id, now.month, now.year)
    return render_template('categories.html', categories=all_categories, category_budgets=category_budgets)

@analytics_bp.route('/categories/budget', methods=['POST'])
@login_required
def set_category_budget():
    user_id = g.user['id']
    category_id = request.form.get('category_id', type=int)
    budget_amount = request.form.get('budget_amount', '0.0')

    try:
        amt = float(budget_amount)
        CategoryBudgetModel.set_budget(user_id, category_id, amt)
        flash('Category budget allocated successfully!', 'success')
    except Exception as e:
        flash(f'Error updating budget: {str(e)}', 'danger')

    return redirect(request.referrer or url_for('analytics.categories_view'))
