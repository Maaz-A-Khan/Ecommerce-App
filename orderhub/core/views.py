import json
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import connection, transaction
from .models import (
    user, product, order_master, order_detail, stock,
    warehouse, category, chart_of_account,
)


def is_admin(u):
    return u.is_authenticated and u.role == 'admin'

admin_required = user_passes_test(is_admin, login_url='core:login')


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        u        = authenticate(request, username=username, password=password)
        if u is not None:
            login(request, u)
            if u.role == 'admin':
                return redirect('core:admin_products')
            return redirect('core:dashboard')
        else:
            messages.error(request, 'Invalid Username or Password.')
    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    return redirect('core:login')


@login_required(login_url='core:login')
def dashboard_view(request):
    if request.user.role == 'admin':
        return redirect('core:admin_products')
    return render(request, 'dashboard.html')


@login_required(login_url='core:login')
def product_list_view(request):
    if request.user.role == 'admin':
        return redirect('core:admin_products')
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT p.code, p.name, p.rate, c.name 
            FROM product p 
            JOIN category c ON p.category_code = c.code
            """
        )
        rows = cursor.fetchall()
    products = [
        {'code': r[0], 'name': r[1], 'rate': r[2], 'category_name': r[3]}
        for r in rows
    ]
    return render(request, 'products.html', {'products': products})


@login_required(login_url='core:login')
def order_checkout_view(request):
    if request.user.role == 'admin':
        return redirect('core:admin_products')

    if request.method == 'POST':
        cart_json = request.POST.get('cart_data', '[]')

        try:
            cart_items = json.loads(cart_json)
        except json.JSONDecodeError:
            messages.error(request, 'Invalid cart data.')
            return redirect('core:checkout')

        if not cart_items:
            messages.error(request, 'Your cart is empty.')
            return redirect('core:checkout')

        for item in cart_items:
            product_code = item.get('code')
            requested_qty = int(item.get('quantity', 0))
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT COALESCE(SUM(receive), 0) - COALESCE(SUM(issue), 0) 
                    FROM stock 
                    WHERE product_code = %s
                    """,
                    [product_code]
                )
                result = cursor.fetchone()
            available = result[0] if result[0] is not None else 0
            if available <= 0 or available < requested_qty:
                messages.error(
                    request,
                    f'Product "{item.get("name", product_code)}" is out of stock or insufficient quantity available.'
                )
                return redirect('core:checkout')

        with connection.cursor() as cursor:
            cursor.execute("SELECT MAX(idno) FROM order_master")
            row = cursor.fetchone()
        last_idno = row[0] if row[0] is not None else 0
        next_num  = last_idno + 1
        entry_no  = f"ORD-{next_num:05d}"

        with connection.cursor() as cursor:
            cursor.execute("SELECT code FROM warehouse LIMIT 1")
            wh_row = cursor.fetchone()
        if not wh_row:
            messages.error(request, 'No warehouse configured. Contact an administrator.')
            return redirect('core:checkout')
        warehouse_code = wh_row[0]

        order_type = 'Purchase Order'

        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO order_master (user_id, order_type, entry_no, order_date) 
                    VALUES (%s, %s, %s, DATE('now'))
                    """,
                    [request.user.id, order_type, entry_no]
                )
                cursor.execute("SELECT last_insert_rowid()")
                om_idno = cursor.fetchone()[0]

            for item in cart_items:
                product_code = item['code']
                qty  = int(item['quantity'])
                rate = Decimal(str(item['rate']))

                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO order_detail (order_master_idno, product_code, warehouse_code, qty, rate) 
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        [om_idno, product_code, warehouse_code, qty, str(rate)]
                    )
                    cursor.execute(
                        """
                        INSERT INTO stock (order_master_idno, warehouse_code, product_code, issue, receive, date) 
                        VALUES (%s, %s, %s, %s, %s, DATE('now'))
                        """,
                        [om_idno, warehouse_code, product_code, qty, 0]
                    )

        messages.success(request, f'Order {entry_no} placed successfully!')
        return redirect('core:customer_dashboard')

    return render(request, 'checkout.html')


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


@login_required(login_url='core:login')
def customer_dashboard_view(request):
    if request.user.role == 'admin':
        return redirect('core:admin_products')

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT idno, entry_no, order_type, order_date 
            FROM order_master 
            WHERE user_id = %s 
            ORDER BY order_date DESC, idno DESC
            """,
            [request.user.id]
        )
        rows = cursor.fetchall()

    orders = [
        {'idno': r[0], 'entry_no': r[1], 'order_type': r[2], 'order_date': r[3]}
        for r in rows
    ]

    return render(request, 'customer_dashboard.html', {'orders': orders})


@login_required(login_url='core:login')
def customer_order_detail_view(request, idno):
    if request.user.role == 'admin':
        return redirect('core:admin_products')

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT idno, entry_no, order_type, order_date 
            FROM order_master 
            WHERE idno = %s AND user_id = %s
            """,
            [idno, request.user.id]
        )
        om_row = cursor.fetchone()

    if not om_row:
        messages.error(request, 'Order not found.')
        return redirect('core:customer_dashboard')

    order = {'idno': om_row[0], 'entry_no': om_row[1], 'order_type': om_row[2], 'order_date': om_row[3]}

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT od.idno, p.name, od.qty, od.rate, (od.qty * od.rate) AS line_total 
            FROM order_detail od 
            JOIN product p ON od.product_code = p.code 
            WHERE od.order_master_idno = %s
            """,
            [idno]
        )
        detail_rows = cursor.fetchall()

    details = [
        {'idno': r[0], 'product_name': r[1], 'qty': r[2], 'rate': r[3], 'line_total': r[4]}
        for r in detail_rows
    ]

    grand_total = sum(d['line_total'] for d in details)

    return render(request, 'customer_order_detail.html', {
        'order':       order,
        'details':     details,
        'grand_total': grand_total,
    })


@login_required(login_url='core:login')
@admin_required
def admin_products_view(request):
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


@login_required(login_url='core:login')
@admin_required
def admin_accounts_view(request):
    customers = chart_of_account.objects.filter(account_type='Customer')
    suppliers = chart_of_account.objects.filter(account_type='Supplier')
    return render(request, 'admin_accounts.html', {
        'customers': customers,
        'suppliers': suppliers,
    })


@login_required(login_url='core:login')
@admin_required
def admin_stock_view(request):
    if request.method == 'POST':
        supplier_code = request.POST.get('supplier', '')
        product_code  = request.POST.get('product', '')
        qty           = int(request.POST.get('quantity', 0))
        rate          = Decimal(request.POST.get('rate', '0'))

        if supplier_code and product_code and qty > 0:
            supplier   = get_object_or_404(chart_of_account, code=supplier_code)
            prod       = get_object_or_404(product, code=product_code)
            default_wh = warehouse.objects.first()

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

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT s.product_code, p.name, COALESCE(SUM(s.receive), 0), COALESCE(SUM(s.issue), 0) 
            FROM stock s 
            JOIN product p ON s.product_code = p.code 
            GROUP BY s.product_code, p.name 
            ORDER BY s.product_code
            """
        )
        stock_rows = cursor.fetchall()

    stock_summary = [
        {
            'product_code':   r[0],
            'product_code__name': r[1],
            'total_receive':  r[2],
            'total_issue':    r[3],
            'available':      r[2] - r[3],
        }
        for r in stock_rows
    ]

    suppliers = chart_of_account.objects.filter(account_type='Supplier')
    products  = product.objects.all()

    return render(request, 'admin_stock.html', {
        'stock_summary': stock_summary,
        'suppliers':     suppliers,
        'products':      products,
    })
