from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from auth import login_required
from models import SubscriptionModel, CategoryModel

subscriptions_bp = Blueprint('subscriptions', __name__)

@subscriptions_bp.route('/subscriptions')
@login_required
def list_subscriptions():
    user_id = g.user['id']
    subscriptions = SubscriptionModel.get_all(user_id)
    summary = SubscriptionModel.get_summary(user_id)
    categories = CategoryModel.get_all(user_id, cat_type='expense')
    today = datetime.now().strftime("%Y-%m-%d")

    return render_template(
        'subscriptions.html',
        subscriptions=subscriptions,
        summary=summary,
        categories=categories,
        today=today
    )

@subscriptions_bp.route('/subscriptions/add', methods=['POST'])
@login_required
def add_subscription():
    user_id = g.user['id']
    title = request.form.get('title', '').strip()
    amount_str = request.form.get('amount', '').strip()
    category_id = request.form.get('category_id', type=int)
    billing_cycle = request.form.get('billing_cycle', 'Monthly').strip()
    next_due_date = request.form.get('next_due_date', '').strip()
    payment_method = request.form.get('payment_method', 'Credit Card').strip()
    notes = request.form.get('notes', '').strip()

    if not title or not amount_str:
        flash('Subscription title and amount are required.', 'danger')
        return redirect(url_for('subscriptions.list_subscriptions'))

    try:
        amount = float(amount_str)
        if amount <= 0:
            flash('Amount must be positive.', 'danger')
            return redirect(url_for('subscriptions.list_subscriptions'))
    except ValueError:
        flash('Invalid amount provided.', 'danger')
        return redirect(url_for('subscriptions.list_subscriptions'))

    SubscriptionModel.create(
        user_id=user_id,
        category_id=category_id,
        title=title,
        amount=amount,
        billing_cycle=billing_cycle,
        next_due_date=next_due_date or None,
        payment_method=payment_method,
        notes=notes
    )
    flash(f'Subscription "{title}" added successfully!', 'success')
    return redirect(url_for('subscriptions.list_subscriptions'))

@subscriptions_bp.route('/subscriptions/<int:sub_id>/edit', methods=['POST'])
@login_required
def edit_subscription(sub_id):
    user_id = g.user['id']
    title = request.form.get('title', '').strip()
    amount_str = request.form.get('amount', '').strip()
    category_id = request.form.get('category_id', type=int)
    billing_cycle = request.form.get('billing_cycle', 'Monthly').strip()
    next_due_date = request.form.get('next_due_date', '').strip()
    payment_method = request.form.get('payment_method', 'Credit Card').strip()
    status = request.form.get('status', 'Active').strip()
    notes = request.form.get('notes', '').strip()

    try:
        amount = float(amount_str)
        SubscriptionModel.update(
            sub_id=sub_id,
            user_id=user_id,
            category_id=category_id,
            title=title,
            amount=amount,
            billing_cycle=billing_cycle,
            next_due_date=next_due_date,
            payment_method=payment_method,
            status=status,
            notes=notes
        )
        flash(f'Subscription "{title}" updated.', 'success')
    except Exception as e:
        flash(f'Error updating subscription: {str(e)}', 'danger')

    return redirect(url_for('subscriptions.list_subscriptions'))

@subscriptions_bp.route('/subscriptions/<int:sub_id>/toggle', methods=['POST'])
@login_required
def toggle_subscription(sub_id):
    user_id = g.user['id']
    new_status = SubscriptionModel.toggle_status(sub_id, user_id)
    if new_status:
        flash(f'Subscription is now {new_status}.', 'info')
    else:
        flash('Unable to update subscription.', 'danger')
    return redirect(url_for('subscriptions.list_subscriptions'))

@subscriptions_bp.route('/subscriptions/<int:sub_id>/delete', methods=['POST'])
@login_required
def delete_subscription(sub_id):
    user_id = g.user['id']
    SubscriptionModel.delete(sub_id, user_id)
    flash('Subscription removed.', 'info')
    return redirect(url_for('subscriptions.list_subscriptions'))

@subscriptions_bp.route('/subscriptions/<int:sub_id>/pay', methods=['POST'])
@login_required
def pay_subscription(sub_id):
    user_id = g.user['id']
    exp_id = SubscriptionModel.record_payment(sub_id, user_id)
    if exp_id:
        flash('Payment recorded as an expense! Next billing date advanced.', 'success')
    else:
        flash('Failed to record recurring payment.', 'danger')
    return redirect(url_for('subscriptions.list_subscriptions'))

