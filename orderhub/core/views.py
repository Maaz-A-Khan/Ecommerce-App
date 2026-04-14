import json
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum, F, Value, DecimalField
from django.db.models.functions import Coalesce
from .models import (
    user, product, order_master, order_detail, stock,
    warehouse, category, chart_of_account,
)


# ═══════════════════════════════════════════════════════════
#  ADMIN GUARD — only users with role == 'admin'
# ═══════════════════════════════════════════════════════════
def is_admin(u):
    return u.is_authenticated and u.role == 'admin'

admin_required = user_passes_test(is_admin, login_url='core:login')


# ═══════════════════════════════════════════════════════════
#  PUBLIC / CUSTOMER VIEWS
# ═══════════════════════════════════════════════════════════

# ── Login ─────────────────────────────────────────────────
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        u        = authenticate(request, username=username, password=password)
        if u is not None:
            login(request, u)
            return redirect('core:dashboard')
        else:
            messages.error(request, 'Invalid Username or Password.')
    return render(request, 'login.html')


# ── Logout ────────────────────────────────────────────────
def logout_view(request):
    logout(request)
    return redirect('core:login')


# ── Dashboard ─────────────────────────────────────────────
@login_required(login_url='core:login')
def dashboard_view(request):
    return render(request, 'dashboard.html')


@login_required(login_url='core:login')
def product_list_view(request):
    products = product.objects.all()
    context = {'products': products}
    return render(request, 'products.html', context)

# ── Order Checkout ────────────────────────────────────────
@login_required(login_url='core:login')
def order_checkout_view(request):
    if request.method == 'POST':
        cart_json   = request.POST.get('cart_data', '[]')
        order_type  = request.POST.get('order_type', 'Regular')

        try:
            cart_items = json.loads(cart_json)
        except json.JSONDecodeError:
            messages.error(request, 'Invalid cart data.')
            return redirect('core:checkout')

        if not cart_items:
            messages.error(request, 'Your cart is empty.')
            return redirect('core:checkout')

        # Generate a unique entry number
        last_order = order_master.objects.order_by('-idno').first()
        next_num   = (last_order.idno + 1) if last_order else 1
        entry_no   = f"ORD-{next_num:05d}"

        # Use the first warehouse (user guarantees at least one exists)
        default_wh = warehouse.objects.first()

        with transaction.atomic():
            # Create order_master (no account_code or total_amount stored)
            om = order_master.objects.create(
                user=request.user,
                order_type=order_type,
                entry_no=entry_no,
            )

            # Create order_detail + stock rows for each cart item
            for item in cart_items:
                prod  = product.objects.get(code=item['code'])
                qty   = int(item['quantity'])
                rate  = Decimal(str(item['rate']))

                order_detail.objects.create(
                    order_master_idno=om,
                    product_code=prod,
                    warehouse_code=default_wh,
                    qty=qty,
                    rate=rate,
                )

                stock.objects.create(
                    order_master_idno=om,
                    warehouse_code=default_wh,
                    product_code=prod,
                    issue=qty,
                    receive=0,
                )

        messages.success(request, f'Order {entry_no} placed successfully!')
        return redirect('core:dashboard')

    return render(request, 'checkout.html')

# ── Register ──────────────────────────────────────────────
def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        name     = request.POST.get('name')
        password = request.POST.get('password')

        if user.objects.filter(username=username).exists():
            return render(request, 'register.html', {'error': 'Username already exists'})

        u = user.objects.create_user(
            username=username,
            name=name,
            password=password
        )
        login(request, u)
        return redirect('core:dashboard')

    return render(request, 'register.html')


# ═══════════════════════════════════════════════════════════
#  ADMIN VIEWS
# ═══════════════════════════════════════════════════════════

# ── Tab 1: Products & Categories ──────────────────────────
@login_required(login_url='core:login')
@admin_required
def admin_products_view(request):
    # Handle Add Product
    if request.method == 'POST' and 'add_product' in request.POST:
        code = request.POST.get('product_code', '').strip()
        name = request.POST.get('product_name', '').strip()
        rate = request.POST.get('product_rate', '0')
        cat  = request.POST.get('product_category', '')

        if code and name and cat:
            if product.objects.filter(code=code).exists():
                messages.error(request, f'Product code "{code}" already exists.')
            else:
                cat_obj = get_object_or_404(category, code=cat)
                product.objects.create(
                    code=code, name=name,
                    rate=Decimal(rate), category_code=cat_obj,
                )
                messages.success(request, f'Product "{name}" added.')
        else:
            messages.error(request, 'All product fields are required.')
        return redirect('core:admin_products')

    # Handle Add Category
    if request.method == 'POST' and 'add_category' in request.POST:
        code = request.POST.get('category_code', '').strip()
        name = request.POST.get('category_name', '').strip()
        if code and name:
            if category.objects.filter(code=code).exists():
                messages.error(request, f'Category code "{code}" already exists.')
            else:
                category.objects.create(code=code, name=name)
                messages.success(request, f'Category "{name}" added.')
        else:
            messages.error(request, 'Category code and name are required.')
        return redirect('core:admin_products')

    context = {
        'products':   product.objects.select_related('category_code').all(),
        'categories': category.objects.all(),
    }
    return render(request, 'admin_products.html', context)


# ── Tab 2: Orders ─────────────────────────────────────────
@login_required(login_url='core:login')
@admin_required
def admin_orders_view(request):
    orders = order_master.objects.select_related('user').order_by('-order_date', '-idno')
    return render(request, 'admin_orders.html', {'orders': orders})


@login_required(login_url='core:login')
@admin_required
def admin_order_detail_view(request, idno):
    order = get_object_or_404(order_master, idno=idno)
    details = order_detail.objects.filter(
        order_master_idno=order
    ).select_related('product_code', 'warehouse_code')
    return render(request, 'admin_order_detail.html', {
        'order':   order,
        'details': details,
    })


# ── Tab 3: Chart of Accounts ─────────────────────────────
@login_required(login_url='core:login')
@admin_required
def admin_accounts_view(request):
    customers = chart_of_account.objects.filter(account_type='Customer')
    suppliers = chart_of_account.objects.filter(account_type='Supplier')
    return render(request, 'admin_accounts.html', {
        'customers': customers,
        'suppliers': suppliers,
    })


# ── Tab 4: Stock & Restocking ────────────────────────────
@login_required(login_url='core:login')
@admin_required
def admin_stock_view(request):
    # Handle Restock Order
    if request.method == 'POST':
        supplier_code = request.POST.get('supplier', '')
        product_code  = request.POST.get('product', '')
        qty           = int(request.POST.get('quantity', 0))
        rate          = Decimal(request.POST.get('rate', '0'))

        if supplier_code and product_code and qty > 0:
            supplier = get_object_or_404(chart_of_account, code=supplier_code)
            prod     = get_object_or_404(product, code=product_code)
            default_wh = warehouse.objects.first()

            # Generate entry number
            last_order = order_master.objects.order_by('-idno').first()
            next_num   = (last_order.idno + 1) if last_order else 1
            entry_no   = f"RST-{next_num:05d}"

            with transaction.atomic():
                om = order_master.objects.create(
                    user=request.user,
                    order_type='Restock Order',
                    entry_no=entry_no,
                )

                order_detail.objects.create(
                    order_master_idno=om,
                    product_code=prod,
                    warehouse_code=default_wh,
                    qty=qty,
                    rate=rate,
                )

                stock.objects.create(
                    order_master_idno=om,
                    warehouse_code=default_wh,
                    product_code=prod,
                    issue=0,
                    receive=qty,
                )

            messages.success(request, f'Restock order {entry_no} created for {qty}× {prod.name}.')
        else:
            messages.error(request, 'All restock fields are required and quantity must be > 0.')
        return redirect('core:admin_stock')

    # Aggregate stock per product: available = sum(receive) - sum(issue)
    stock_summary = stock.objects.values(
        'product_code',
        'product_code__name',
    ).annotate(
        total_receive=Coalesce(Sum('receive'), 0),
        total_issue=Coalesce(Sum('issue'), 0),
    ).order_by('product_code')

    # Calculate available qty in Python (safe for all DBs)
    for row in stock_summary:
        row['available'] = row['total_receive'] - row['total_issue']

    suppliers = chart_of_account.objects.filter(account_type='Supplier')
    products  = product.objects.all()

    return render(request, 'admin_stock.html', {
        'stock_summary': stock_summary,
        'suppliers':     suppliers,
        'products':      products,
    })
