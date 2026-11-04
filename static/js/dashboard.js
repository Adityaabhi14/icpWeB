// SpendWise Dashboard, Charts & UI Event Handling

let categoryChartInstance = null;
let trendChartInstance = null;

// Modal Controls
function openAddExpenseModal(defaultType = 'expense') {
    const modal = document.getElementById('addExpenseModal');
    if (modal) {
        const typeRadios = modal.querySelectorAll('input[name="type"]');
        typeRadios.forEach(radio => {
            if (radio.value === defaultType) {
                radio.checked = true;
            }
        });
        toggleTypeCategories(defaultType);
        modal.classList.remove('hidden');
        modal.classList.add('flex');
    }
}

function closeAddExpenseModal() {
    const modal = document.getElementById('addExpenseModal');
    if (modal) {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
    }
}

async function openEditExpenseModal(expenseId) {
    if (!expenseId) return;
    try {
        const response = await fetch(`/expenses/${expenseId}/json`);
        if (!response.ok) {
            throw new Error('Failed to fetch transaction details');
        }
        const data = await response.json();

        const form = document.getElementById('editExpenseForm');
        form.action = `/expenses/${data.id}/edit`;
        document.getElementById('edit_title').value = data.title;
        document.getElementById('edit_amount').value = data.amount;
        document.getElementById('edit_date').value = data.date;
        document.getElementById('edit_type').value = data.type || 'expense';
        document.getElementById('edit_category_id').value = data.category_id || '';
        document.getElementById('edit_payment_method').value = data.payment_method;
        document.getElementById('edit_notes').value = data.notes || '';

        const receiptPreview = document.getElementById('edit_receipt_preview');
        if (receiptPreview) {
            if (data.receipt_filename) {
                receiptPreview.innerHTML = `
                    <div class="flex items-center justify-between p-2 rounded-lg bg-slate-50 border border-slate-200 text-xs">
                        <span class="text-slate-600 truncate"><i class="fas fa-file-invoice mr-1 text-brand-600"></i> ${data.receipt_filename}</span>
                        <a href="/uploads/receipts/${data.receipt_filename}" target="_blank" class="text-brand-600 font-bold hover:underline">View</a>
                    </div>
                `;
            } else {
                receiptPreview.innerHTML = '<span class="text-xs text-slate-400">No receipt attached</span>';
            }
        }

        const modal = document.getElementById('editExpenseModal');
        modal.classList.remove('hidden');
        modal.classList.add('flex');
    } catch (err) {
        alert('Could not load transaction details: ' + err.message);
    }
}

function closeEditExpenseModal() {
    const modal = document.getElementById('editExpenseModal');
    if (modal) {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
    }
}

function openReceiptModal(url, title = 'Receipt Attachment') {
    const modal = document.getElementById('receiptViewModal');
    const container = document.getElementById('receiptModalContent');
    const titleEl = document.getElementById('receiptModalTitle');

    if (modal && container) {
        titleEl.textContent = title;
        if (url.toLowerCase().endsWith('.pdf')) {
            container.innerHTML = `<iframe src="${url}" class="w-full h-[70vh] rounded-xl border border-slate-200"></iframe>`;
        } else {
            container.innerHTML = `<img src="${url}" alt="Receipt" class="max-h-[70vh] mx-auto rounded-xl object-contain shadow">`;
        }
        modal.classList.remove('hidden');
        modal.classList.add('flex');
    }
}

function closeReceiptModal() {
    const modal = document.getElementById('receiptViewModal');
    if (modal) {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
    }
}

function openImportModal() {
    const modal = document.getElementById('importModal');
    if (modal) {
        modal.classList.remove('hidden');
        modal.classList.add('flex');
    }
}

function closeImportModal() {
    const modal = document.getElementById('importModal');
    if (modal) {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
    }
}

function toggleTypeCategories(type) {
    const catSelect = document.getElementById('add_category_id');
    if (!catSelect) return;
    const options = catSelect.querySelectorAll('option');
    options.forEach(opt => {
        const optType = opt.getAttribute('data-type');
        if (!optType || optType === type) {
            opt.style.display = '';
        } else {
            opt.style.display = 'none';
        }
    });
}

// Chart Initializations
async function initDashboardCharts(month, year, currencySymbol = '$') {
    const categoryCanvas = document.getElementById('categoryChart');
    const trendCanvas = document.getElementById('trendChart');

    if (!categoryCanvas && !trendCanvas) return;

    try {
        const response = await fetch(`/api/chart-data?month=${month}&year=${year}`);
        const data = await response.json();

        // 1. Category Breakdown (Doughnut Chart)
        if (categoryCanvas) {
            if (categoryChartInstance) {
                categoryChartInstance.destroy();
            }

            const ctx = categoryCanvas.getContext('2d');
            const hasData = data.categories.totals.length > 0 && data.categories.totals.some(v => v > 0);

            if (!hasData) {
                document.getElementById('noCategoryDataMessage')?.classList.remove('hidden');
                categoryCanvas.classList.add('hidden');
            } else {
                document.getElementById('noCategoryDataMessage')?.classList.add('hidden');
                categoryCanvas.classList.remove('hidden');

                categoryChartInstance = new Chart(ctx, {
                    type: 'doughnut',
                    data: {
                        labels: data.categories.labels,
                        datasets: [{
                            data: data.categories.totals,
                            backgroundColor: data.categories.colors,
                            borderWidth: 2,
                            borderColor: '#ffffff',
                            hoverOffset: 6
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                position: 'bottom',
                                labels: {
                                    boxWidth: 12,
                                    padding: 12,
                                    font: { family: "'Plus Jakarta Sans', sans-serif", size: 11 }
                                }
                            },
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        const label = context.label || '';
                                        const value = context.parsed || 0;
                                        const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                        const pct = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                                        return ` ${label}: ${currencySymbol}${value.toLocaleString()} (${pct}%)`;
                                    }
                                }
                            }
                        },
                        cutout: '66%'
                    }
                });
            }
        }

        // 2. Dual Trend Comparison: Incomes vs Expenses
        if (trendCanvas) {
            if (trendChartInstance) {
                trendChartInstance.destroy();
            }

            const ctx = trendCanvas.getContext('2d');
            trendChartInstance = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: data.trends.labels,
                    datasets: [
                        {
                            label: 'Expenses',
                            data: data.trends.expenses,
                            backgroundColor: 'rgba(239, 68, 68, 0.85)',
                            hoverBackgroundColor: 'rgba(220, 38, 38, 1)',
                            borderRadius: 6
                        },
                        {
                            label: 'Income',
                            data: data.trends.income,
                            backgroundColor: 'rgba(16, 185, 129, 0.85)',
                            hoverBackgroundColor: 'rgba(5, 150, 105, 1)',
                            borderRadius: 6
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { color: 'rgba(226, 232, 240, 0.6)' },
                            ticks: {
                                callback: function(value) {
                                    return currencySymbol + value.toLocaleString();
                                },
                                font: { family: "'Plus Jakarta Sans', sans-serif", size: 11 }
                            }
                        },
                        x: {
                            grid: { display: false },
                            ticks: { font: { family: "'Plus Jakarta Sans', sans-serif", size: 11 } }
                        }
                    },
                    plugins: {
                        legend: {
                            position: 'top',
                            labels: {
                                boxWidth: 12,
                                font: { family: "'Plus Jakarta Sans', sans-serif", size: 12 }
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return ` ${context.dataset.label}: ${currencySymbol}${context.parsed.y.toLocaleString()}`;
                                }
                            }
                        }
                    }
                }
            });
        }
    } catch (error) {
        console.error('Error loading chart data:', error);
    }
}

// Global delegated click handlers for receipts, edit buttons, and modals
document.addEventListener('click', function(e) {
    const receiptBtn = e.target.closest('.btn-receipt-view');
    if (receiptBtn) {
        const url = receiptBtn.getAttribute('data-receipt-url');
        const title = receiptBtn.getAttribute('data-receipt-title') || 'Receipt Attachment';
        openReceiptModal(url, title);
        return;
    }

    const editBtn = e.target.closest('.btn-edit-expense');
    if (editBtn) {
        const id = editBtn.getAttribute('data-expense-id');
        openEditExpenseModal(id);
        return;
    }
});

// Global modal dismiss on ESC
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        closeAddExpenseModal();
        closeEditExpenseModal();
        closeReceiptModal();
        closeImportModal();
        const subModal = document.getElementById('addSubModal');
        if (subModal) {
            subModal.classList.add('hidden');
            subModal.classList.remove('flex');
        }
    }
});

// Auto-initialize components on DOMContentLoaded
document.addEventListener('DOMContentLoaded', function() {
    // 1. Apply category colors dynamically without violating CSS syntax in templates
    document.querySelectorAll('[data-cat-color]').forEach(function(el) {
        const color = el.getAttribute('data-cat-color');
        if (color) {
            el.style.color = color;
            el.style.backgroundColor = color + '1a';
        }
    });

    // 2. Animate progress bars from data-width
    document.querySelectorAll('[data-width]').forEach(function(el) {
        const width = el.getAttribute('data-width');
        if (width !== null) {
            el.style.width = width + '%';
        }
    });

    // 3. Connect period selector if on dashboard
    const periodSelect = document.getElementById('periodSelect');
    if (periodSelect) {
        periodSelect.addEventListener('change', function() {
            const parts = this.value.split('-');
            if (parts.length === 2) {
                window.location.href = '/dashboard?month=' + parts[0] + '&year=' + parts[1];
            }
        });
    }

    // 4. Auto-initialize dashboard charts from data attributes
    const metricsEl = document.getElementById('dashboardMetricsData');
    if (metricsEl) {
        const m = metricsEl.getAttribute('data-month');
        const y = metricsEl.getAttribute('data-year');
        const curr = metricsEl.getAttribute('data-currency') || '$';
        initDashboardCharts(m, y, curr);
    }

    // 5. Auto-dismiss flash alerts
    const alerts = document.querySelectorAll('.flash-alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    });
});
