import csv
import io
import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, g,
    jsonify, Response, current_app, send_from_directory
)
from auth import login_required
from models import ExpenseModel, CategoryModel

expenses_bp = Blueprint('expenses', __name__)

PAYMENT_METHODS = ['Credit Card', 'Debit Card', 'Cash', 'UPI / Online', 'Bank Transfer', 'Other']

def allowed_file(filename):
    allowed_exts = current_app.config.get('ALLOWED_EXTENSIONS', {'png', 'jpg', 'jpeg', 'webp', 'pdf'})
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_exts

def save_receipt_file(file_storage):
    if not file_storage or file_storage.filename == '':
        return None
    if not allowed_file(file_storage.filename):
        return None

    ext = file_storage.filename.rsplit('.', 1)[1].lower()
    unique_name = f"receipt_{uuid.uuid4().hex[:12]}_{int(datetime.now().timestamp())}.{ext}"
    upload_folder = current_app.config.get('UPLOAD_FOLDER')
    os.makedirs(upload_folder, exist_ok=True)
    file_storage.save(os.path.join(upload_folder, unique_name))
    return unique_name

@expenses_bp.route('/expenses')
@login_required
def list_expenses():
    user_id = g.user['id']
    page = request.args.get('page', 1, type=int)
    limit = current_app.config.get('ITEMS_PER_PAGE', 10)
    offset = (page - 1) * limit

    search = request.args.get('search', '').strip()
    category_id = request.args.get('category_id', type=int)
    payment_method = request.args.get('payment_method', '').strip()
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    exp_type = request.args.get('type', '').strip() or None

    expenses = ExpenseModel.filter_expenses(
        user_id=user_id,
        start_date=start_date or None,
        end_date=end_date or None,
        category_id=category_id or None,
        payment_method=payment_method or None,
        search=search or None,
        exp_type=exp_type,
        limit=limit,
        offset=offset
    )

    total_count = ExpenseModel.count_expenses(
        user_id=user_id,
        start_date=start_date or None,
        end_date=end_date or None,
        category_id=category_id or None,
        payment_method=payment_method or None,
        search=search or None,
        exp_type=exp_type
    )

    total_pages = max(1, (total_count + limit - 1) // limit)
    categories = CategoryModel.get_all(user_id)

    today = datetime.now().strftime("%Y-%m-%d")

    return render_template(
        'expenses.html',
        expenses=expenses,
        categories=categories,
        payment_methods=PAYMENT_METHODS,
        page=page,
        total_pages=total_pages,
        total_count=total_count,
        search=search,
        selected_category=category_id,
        selected_payment_method=payment_method,
        selected_type=exp_type or '',
        start_date=start_date,
        end_date=end_date,
        today=today
    )

@expenses_bp.route('/expenses/add', methods=['POST'])
@login_required
def add_expense():
    user_id = g.user['id']
    title = request.form.get('title', '').strip()
    amount_str = request.form.get('amount', '').strip()
    date = request.form.get('date', '').strip()
    category_id = request.form.get('category_id', type=int)
    payment_method = request.form.get('payment_method', 'Credit Card').strip()
    notes = request.form.get('notes', '').strip()
    exp_type = request.form.get('type', 'expense').strip()
    if exp_type not in ('expense', 'income'):
        exp_type = 'expense'

    receipt_file = request.files.get('receipt')
    receipt_filename = save_receipt_file(receipt_file) if receipt_file else None

    error = None
    if not title:
        error = 'Title is required.'
    elif not amount_str:
        error = 'Amount is required.'
    else:
        try:
            amount = float(amount_str)
            if amount <= 0:
                error = 'Amount must be greater than zero.'
        except ValueError:
            error = 'Please enter a valid numeric amount.'

    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    if error:
        flash(error, 'danger')
        return redirect(request.referrer or url_for('expenses.list_expenses'))

    try:
        ExpenseModel.create(
            user_id=user_id,
            category_id=category_id,
            title=title,
            amount=float(amount_str),
            date=date,
            payment_method=payment_method,
            notes=notes,
            exp_type=exp_type,
            receipt_filename=receipt_filename
        )
        label = 'Income deposit' if exp_type == 'income' else 'Expense'
        flash(f'{label} "{title}" of {g.user["currency"]}{float(amount_str):,.2f} recorded successfully!', 'success')
    except Exception as e:
        flash(f'Error adding transaction: {str(e)}', 'danger')

    return redirect(request.referrer or url_for('expenses.list_expenses'))

@expenses_bp.route('/expenses/<int:expense_id>/json')
@login_required
def get_expense_json(expense_id):
    expense = ExpenseModel.get_by_id(expense_id, g.user['id'])
    if not expense:
        return jsonify({'error': 'Expense not found'}), 404

    return jsonify({
        'id': expense['id'],
        'title': expense['title'],
        'amount': expense['amount'],
        'type': expense['type'],
        'date': expense['date'],
        'category_id': expense['category_id'],
        'payment_method': expense['payment_method'],
        'notes': expense['notes'] or '',
        'receipt_filename': expense['receipt_filename'] or ''
    })

@expenses_bp.route('/expenses/<int:expense_id>/edit', methods=['POST'])
@login_required
def edit_expense(expense_id):
    user_id = g.user['id']
    expense = ExpenseModel.get_by_id(expense_id, user_id)
    if not expense:
        flash('Transaction record not found.', 'danger')
        return redirect(url_for('expenses.list_expenses'))

    title = request.form.get('title', '').strip()
    amount_str = request.form.get('amount', '').strip()
    date = request.form.get('date', '').strip()
    category_id = request.form.get('category_id', type=int)
    payment_method = request.form.get('payment_method', 'Credit Card').strip()
    notes = request.form.get('notes', '').strip()
    exp_type = request.form.get('type', 'expense').strip()
    if exp_type not in ('expense', 'income'):
        exp_type = 'expense'

    receipt_file = request.files.get('receipt')
    receipt_filename = save_receipt_file(receipt_file) if receipt_file else None

    try:
        amount = float(amount_str)
        ExpenseModel.update(
            expense_id=expense_id,
            user_id=user_id,
            category_id=category_id,
            title=title,
            amount=amount,
            date=date,
            payment_method=payment_method,
            notes=notes,
            exp_type=exp_type,
            receipt_filename=receipt_filename
        )
        flash(f'Transaction "{title}" updated successfully!', 'success')
    except Exception as e:
        flash(f'Error updating transaction: {str(e)}', 'danger')

    return redirect(request.referrer or url_for('expenses.list_expenses'))

@expenses_bp.route('/expenses/<int:expense_id>/delete', methods=['POST'])
@login_required
def delete_expense(expense_id):
    user_id = g.user['id']
    success = ExpenseModel.delete(expense_id, user_id)
    if success:
        flash('Transaction deleted successfully.', 'info')
    else:
        flash('Unable to delete transaction.', 'danger')
    return redirect(request.referrer or url_for('expenses.list_expenses'))

@expenses_bp.route('/uploads/receipts/<filename>')
@login_required
def get_receipt_file(filename):
    upload_folder = current_app.config.get('UPLOAD_FOLDER')
    safe_name = secure_filename(filename)
    return send_from_directory(upload_folder, safe_name)

@expenses_bp.route('/expenses/export')
@login_required
def export_csv():
    user_id = g.user['id']
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    category_id = request.args.get('category_id', type=int)
    payment_method = request.args.get('payment_method', '').strip()
    search = request.args.get('search', '').strip()
    exp_type = request.args.get('type', '').strip() or None

    expenses = ExpenseModel.filter_expenses(
        user_id=user_id,
        start_date=start_date or None,
        end_date=end_date or None,
        category_id=category_id or None,
        payment_method=payment_method or None,
        search=search or None,
        exp_type=exp_type,
        limit=None,
        offset=0
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Date', 'Type', 'Title', 'Amount', 'Currency', 'Category', 'Payment Method', 'Notes', 'Created At'])

    for e in expenses:
        writer.writerow([
            e['id'],
            e['date'],
            e['type'].upper(),
            e['title'],
            f"{e['amount']:.2f}",
            g.user['currency'],
            e['category_name'] or 'Uncategorized',
            e['payment_method'],
            e['notes'] or '',
            e['created_at']
        ])

    csv_data = output.getvalue()
    filename = f"transactions_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@expenses_bp.route('/expenses/import', methods=['POST'])
@login_required
def import_csv():
    file = request.files.get('csv_file')
    if not file or file.filename == '':
        flash('Please select a valid CSV file to import.', 'danger')
        return redirect(url_for('expenses.list_expenses'))

    if not file.filename.lower().endswith('.csv'):
        flash('Only CSV format files can be imported.', 'danger')
        return redirect(url_for('expenses.list_expenses'))

    try:
        count = ExpenseModel.bulk_import_csv(g.user['id'], file.stream)
        flash(f'Successfully imported {count} transactions from CSV!', 'success')
    except Exception as e:
        flash(f'Error importing CSV: {str(e)}', 'danger')

    return redirect(url_for('expenses.list_expenses'))
