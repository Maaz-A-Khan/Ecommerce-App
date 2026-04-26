import json
from decimal import Decimal
from django.shortcuts import render, redirect
from django.http import Http404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import connection, transaction
from .models import (
    user, product, order_master, order_detail, stock,
    warehouse, category, chart_of_account,
    region, product_bundle, bundle_item,
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
        city      = request.POST.get('city', '').strip()
        country   = request.POST.get('country', '').strip()

        try:
            cart_items = json.loads(cart_json)
        except json.JSONDecodeError:
            messages.error(request, 'Invalid cart data.')
            return redirect('core:checkout')

        if not cart_items:
            messages.error(request, 'Your cart is empty.')
            return redirect('core:checkout')

        if not city or not country:
            messages.error(request, 'City and Country are required.')
            return redirect('core:checkout')

        with connection.cursor() as cursor:
            cursor.execute("SELECT code FROM warehouse LIMIT 1")
            wh_row = cursor.fetchone()
        if not wh_row:
            messages.error(request, 'No warehouse configured. Contact an administrator.')
            return redirect('core:checkout')
        warehouse_code = wh_row[0]

        order_type = 'Purchase Order'

        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    # Step A: Region handling
                    cursor.execute(
                        """
                        SELECT idno FROM region
                        WHERE LOWER(city) = LOWER(%s) AND LOWER(country) = LOWER(%s)
                        """,
                        [city, country]
                    )
                    region_row = cursor.fetchone()
                    if region_row:
                        region_idno = region_row[0]
                    else:
                        cursor.execute(
                            "INSERT INTO region (city, country) VALUES (%s, %s) RETURNING idno",
                            [city, country]
                        )
                        region_idno = cursor.fetchone()[0]

                    # Step B: Lazy account initialization
                    if not request.user.account_code:
                        cursor.execute(
                            """
                            SELECT code
                            FROM chart_of_account
                            WHERE account_type = 'Customer' AND code LIKE 'CUST-%%'
                            ORDER BY CAST(SUBSTRING(code FROM 6) AS INTEGER) DESC
                            LIMIT 1
                            """
                        )
                        last_code_row = cursor.fetchone()

                        if last_code_row is None:
                            new_code = 'CUST-1001'
                        else:
                            try:
                                last_int = int(last_code_row[0].split('-')[1])
                            except (IndexError, ValueError):
                                last_int = 1000
                            new_code = f"CUST-{last_int + 1}"

                        cursor.execute(
                            """
                            INSERT INTO chart_of_account (code, name, account_type, region_idno)
                            VALUES (%s, %s, 'Customer', %s)
                            """,
                            [new_code, request.user.username, region_idno]
                        )
                        cursor.execute(
                            "UPDATE \"user\" SET account_code = %s WHERE id = %s",
                            [new_code, request.user.id]
                        )
                        request.user.account_code_id = new_code
                    else:
                        # Update existing account with latest region
                        cursor.execute(
                            "UPDATE chart_of_account SET region_idno = %s WHERE code = %s",
                            [region_idno, request.user.account_code_id]
                        )

                    # Step C: Generate entry_no and insert order_master
                    cursor.execute("SELECT MAX(idno) FROM order_master")
                    row = cursor.fetchone()
                    last_idno = row[0] if row[0] is not None else 0
                    next_num  = last_idno + 1
                    entry_no  = f"ORD-{next_num:05d}"

                    cursor.execute(
                        """
                        INSERT INTO order_master (user_id, order_type, entry_no, order_date)
                        VALUES (%s, %s, %s, CURRENT_DATE)
                        RETURNING idno
                        """,
                        [request.user.id, order_type, entry_no]
                    )
                    om_idno = cursor.fetchone()[0]

                    # Step D: Process cart items (bundle unpacking)
                    for item in cart_items:
                        item_code = item['code']
                        cart_qty  = int(item['quantity'])
                        cart_rate = Decimal(str(item['rate']))

                        cursor.execute(
                            """
                            SELECT code
                            FROM product_bundle
                            WHERE code = %s AND is_active = TRUE
                            """,
                            [item_code]
                        )
                        bundle_row = cursor.fetchone()

                        if bundle_row is None:
                            cursor.execute(
                                """
                                SELECT COALESCE(SUM(receive), 0) - COALESCE(SUM(issue), 0)
                                FROM stock
                                WHERE product_code = %s
                                """,
                                [item_code]
                            )
                            stock_result = cursor.fetchone()
                            available = stock_result[0] if stock_result[0] is not None else 0
                            if available < cart_qty:
                                messages.error(
                                    request,
                                    f'Product "{item.get("name", item_code)}" has insufficient stock.'
                                )
                                raise Exception('stock_failure')

                            cursor.execute(
                                """
                                INSERT INTO order_detail
                                    (order_master_idno, product_code, warehouse_code, qty, rate)
                                VALUES (%s, %s, %s, %s, %s)
                                """,
                                [om_idno, item_code, warehouse_code, cart_qty, str(cart_rate)]
                            )
                            cursor.execute(
                                """
                                INSERT INTO stock
                                    (order_master_idno, warehouse_code, product_code, issue, receive, date)
                                VALUES (%s, %s, %s, %s, %s, CURRENT_DATE)
                                """,
                                [om_idno, warehouse_code, item_code, cart_qty, 0]
                            )
                        else:
                            cursor.execute(
                                """
                                SELECT bi.product_code, p.rate, pb.discount_percentage, bi.qty_included
                                FROM bundle_item bi
                                JOIN product p ON bi.product_code = p.code
                                JOIN product_bundle pb ON bi.bundle_code = pb.code
                                WHERE bi.bundle_code = %s
                                """,
                                [item_code]
                            )
                            bundle_products = cursor.fetchall()

                            for bp_code, bp_rate, bp_discount, bp_qty_included in bundle_products:
                                required_qty    = cart_qty * bp_qty_included
                                discounted_rate = Decimal(str(bp_rate)) * (1 - Decimal(str(bp_discount)) / 100)

                                cursor.execute(
                                    """
                                    SELECT COALESCE(SUM(receive), 0) - COALESCE(SUM(issue), 0)
                                    FROM stock
                                    WHERE product_code = %s
                                    """,
                                    [bp_code]
                                )
                                bp_stock = cursor.fetchone()
                                bp_available = bp_stock[0] if bp_stock[0] is not None else 0
                                if bp_available < required_qty:
                                    messages.error(
                                        request,
                                        f'Bundle item "{bp_code}" has insufficient stock for bundle "{item_code}".'
                                    )
                                    raise Exception('stock_failure')

                                cursor.execute(
                                    """
                                    INSERT INTO order_detail
                                        (order_master_idno, product_code, warehouse_code, qty, rate)
                                    VALUES (%s, %s, %s, %s, %s)
                                    """,
                                    [om_idno, bp_code, warehouse_code, required_qty, str(discounted_rate)]
                                )
                                cursor.execute(
                                    """
                                    INSERT INTO stock
                                        (order_master_idno, warehouse_code, product_code, issue, receive, date)
                                    VALUES (%s, %s, %s, %s, %s, CURRENT_DATE)
                                    """,
                                    [om_idno, warehouse_code, bp_code, required_qty, 0]
                                )

        except Exception as e:
            if str(e) != 'stock_failure':
                messages.error(request, 'An unexpected error occurred during checkout.')
            return redirect('core:checkout')

        messages.success(request, f'Order {entry_no} placed successfully!')
        return redirect('core:customer_dashboard')

    return render(request, 'checkout.html')


def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        name     = request.POST.get('name')
        password = request.POST.get('password')

        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM \"user\" WHERE username = %s LIMIT 1", [username])
            if cursor.fetchone():
                return render(request, 'register.html', {'error': 'Username already exists'})

            hashed_password = make_password(password)
            cursor.execute(
                """
                INSERT INTO "user" (username, name, password, is_superuser, is_staff, is_active, first_name, last_name, email, date_joined, role)
                VALUES (%s, %s, %s, FALSE, FALSE, TRUE, '', '', '', NOW(), 'customer')
                """,
                [username, name, hashed_password]
            )

        u = authenticate(request, username=username, password=password)
        if u is not None:
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


# ═══════════════════════════════════════════════════════════
#  ADMIN VIEWS
# ═══════════════════════════════════════════════════════════

@login_required(login_url='core:login')
@admin_required
def admin_products_view(request):
    if request.method == 'POST' and 'add_product' in request.POST:
        name = request.POST.get('product_name', '').strip()
        rate = request.POST.get('product_rate', '0')
        cat  = request.POST.get('product_category', '')

        if name and cat:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM category WHERE code = %s LIMIT 1", [cat])
                if not cursor.fetchone():
                    raise Http404("Category not found")

                cursor.execute(
                    """
                    SELECT code FROM product
                    WHERE code LIKE 'PRD-%%'
                    ORDER BY CAST(SUBSTRING(code FROM 5) AS INTEGER) DESC
                    LIMIT 1
                    """
                )
                last_row = cursor.fetchone()
                if last_row is None:
                    code = 'PRD-001'
                else:
                    try:
                        last_int = int(last_row[0].split('-')[1])
                    except (IndexError, ValueError):
                        last_int = 0
                    code = f"PRD-{last_int + 1:03d}"

                cursor.execute(
                    "INSERT INTO product (code, name, rate, category_code) VALUES (%s, %s, %s, %s)",
                    [code, name, rate, cat]
                )
                messages.success(request, f'Product "{name}" added as {code}.')
        else:
            messages.error(request, 'Product name, rate, and category are required.')
        return redirect('core:admin_products')

    if request.method == 'POST' and 'add_category' in request.POST:
        name = request.POST.get('category_name', '').strip()
        if name:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT code FROM category
                    WHERE code LIKE 'CAT-%%'
                    ORDER BY CAST(SUBSTRING(code FROM 5) AS INTEGER) DESC
                    LIMIT 1
                    """
                )
                last_row = cursor.fetchone()
                if last_row is None:
                    code = 'CAT-001'
                else:
                    try:
                        last_int = int(last_row[0].split('-')[1])
                    except (IndexError, ValueError):
                        last_int = 0
                    code = f"CAT-{last_int + 1:03d}"

                cursor.execute("INSERT INTO category (code, name) VALUES (%s, %s)", [code, name])
                messages.success(request, f'Category "{name}" added as {code}.')
        else:
            messages.error(request, 'Category name is required.')
        return redirect('core:admin_products')

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT p.code, p.name, p.rate, p.category_code, c.name 
            FROM product p 
            JOIN category c ON p.category_code = c.code 
            ORDER BY p.code
            """
        )
        products = [
            {
                'code': r[0],
                'name': r[1],
                'rate': r[2],
                'category_code': {'name': r[4]}
            }
            for r in cursor.fetchall()
        ]

        cursor.execute("SELECT code, name FROM category ORDER BY code")
        categories = [{'code': r[0], 'name': r[1]} for r in cursor.fetchall()]

    context = {
        'products': products,
        'categories': categories,
    }
    return render(request, 'admin_products.html', context)


@login_required(login_url='core:login')
@admin_required
def delete_product_view(request, code):
    if request.method == 'POST':
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM stock WHERE product_code = %s LIMIT 1", [code])
            if cursor.fetchone():
                messages.error(request, f'Cannot delete product "{code}" — it has stock records.')
            else:
                cursor.execute("DELETE FROM product WHERE code = %s", [code])
                messages.success(request, f'Product "{code}" deleted.')
    return redirect('core:admin_products')


@login_required(login_url='core:login')
@admin_required
def delete_category_view(request, code):
    if request.method == 'POST':
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM product WHERE category_code = %s LIMIT 1", [code])
            if cursor.fetchone():
                messages.error(request, f'Cannot delete category "{code}" — it still has products.')
            else:
                cursor.execute("DELETE FROM category WHERE code = %s", [code])
                messages.success(request, f'Category "{code}" deleted.')
    return redirect('core:admin_products')


@login_required(login_url='core:login')
@admin_required
def admin_orders_view(request):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT o.idno, o.entry_no, o.order_type, o.order_date, u.name, u.username
            FROM order_master o
            JOIN "user" u ON o.user_id = u.id
            ORDER BY o.order_date DESC, o.idno DESC
            """
        )
        orders = [
            {
                'idno': r[0],
                'entry_no': r[1],
                'order_type': r[2],
                'order_date': r[3],
                'user': {'name': r[4], 'username': r[5]}
            }
            for r in cursor.fetchall()
        ]
    return render(request, 'admin_orders.html', {'orders': orders})


@login_required(login_url='core:login')
@admin_required
def admin_order_detail_view(request, idno):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT o.idno, o.entry_no, o.order_type, o.order_date, u.name, u.username
            FROM order_master o
            JOIN "user" u ON o.user_id = u.id
            WHERE o.idno = %s
            """,
            [idno]
        )
        row = cursor.fetchone()
        if not row:
            raise Http404("Order not found")

        order = {
            'idno': row[0],
            'entry_no': row[1],
            'order_type': row[2],
            'order_date': row[3],
            'user': {'name': row[4], 'username': row[5]}
        }

        cursor.execute(
            """
            SELECT od.qty, od.rate, p.code, p.name, w.name
            FROM order_detail od
            JOIN product p ON od.product_code = p.code
            JOIN warehouse w ON od.warehouse_code = w.code
            WHERE od.order_master_idno = %s
            """,
            [idno]
        )
        details = [
            {
                'qty': r[0],
                'rate': r[1],
                'product_code': {'code': r[2], 'name': r[3]},
                'warehouse_code': {'name': r[4]}
            }
            for r in cursor.fetchall()
        ]

    return render(request, 'admin_order_detail.html', {
        'order':   order,
        'details': details,
    })


@login_required(login_url='core:login')
@admin_required
def admin_accounts_view(request):
    if request.method == 'POST' and 'add_supplier' in request.POST:
        name = request.POST.get('supplier_name', '').strip()
        if name:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT code
                    FROM chart_of_account
                    WHERE account_type = 'Supplier' AND code LIKE 'SUPP-%%'
                    ORDER BY CAST(SUBSTRING(code FROM 6) AS INTEGER) DESC
                    LIMIT 1
                    """
                )
                last_row = cursor.fetchone()
                if last_row is None:
                    new_code = 'SUPP-1001'
                else:
                    try:
                        last_int = int(last_row[0].split('-')[1])
                    except (IndexError, ValueError):
                        last_int = 1000
                    new_code = f"SUPP-{last_int + 1}"

                cursor.execute(
                    """
                    INSERT INTO chart_of_account (code, name, account_type, region_idno)
                    VALUES (%s, %s, 'Supplier', NULL)
                    """,
                    [new_code, name]
                )
                unusable_pw = make_password(None)
                cursor.execute(
                    """
                    INSERT INTO "user" (username, name, password, is_superuser, is_staff, is_active,
                                        first_name, last_name, email, date_joined, role, account_code)
                    VALUES (%s, %s, %s, FALSE, FALSE, FALSE, '', '', '', NOW(), 'supplier', %s)
                    """,
                    [new_code, name, unusable_pw, new_code]
                )
                messages.success(request, f'Supplier "{name}" added as {new_code}.')
        else:
            messages.error(request, 'Supplier name is required.')
        return redirect('core:admin_accounts')

    with connection.cursor() as cursor:
        cursor.execute("SELECT code, name, account_type FROM chart_of_account WHERE account_type = 'Customer' ORDER BY code")
        customers = [{'code': r[0], 'name': r[1], 'account_type': r[2]} for r in cursor.fetchall()]

        cursor.execute("SELECT code, name, account_type FROM chart_of_account WHERE account_type = 'Supplier' ORDER BY code")
        suppliers = [{'code': r[0], 'name': r[1], 'account_type': r[2]} for r in cursor.fetchall()]

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

        if supplier_code and product_code and qty > 0:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT id FROM \"user\" WHERE account_code = %s AND role = 'supplier' LIMIT 1",
                        [supplier_code]
                    )
                    supplier_user_row = cursor.fetchone()
                    if not supplier_user_row:
                        raise Http404("Supplier not found")
                    supplier_user_id = supplier_user_row[0]

                    cursor.execute("SELECT name, rate FROM product WHERE code = %s LIMIT 1", [product_code])
                    prod_row = cursor.fetchone()
                    if not prod_row:
                        raise Http404("Product not found")
                    prod_name = prod_row[0]
                    rate      = prod_row[1]

                    cursor.execute("SELECT code FROM warehouse LIMIT 1")
                    wh_row = cursor.fetchone()
                    if not wh_row:
                        raise Http404("Warehouse not found")
                    default_wh = wh_row[0]

                    cursor.execute("SELECT MAX(idno) FROM order_master")
                    last_order_row = cursor.fetchone()
                    last_idno = last_order_row[0] if last_order_row[0] is not None else 0
                    next_num = last_idno + 1
                    entry_no = f"RST-{next_num:05d}"

                    cursor.execute(
                        """
                        INSERT INTO order_master (user_id, order_type, entry_no, order_date)
                        VALUES (%s, 'Restock Order', %s, CURRENT_DATE)
                        RETURNING idno
                        """,
                        [supplier_user_id, entry_no]
                    )
                    om_idno = cursor.fetchone()[0]

                    cursor.execute(
                        """
                        INSERT INTO order_detail (order_master_idno, product_code, warehouse_code, qty, rate)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        [om_idno, product_code, default_wh, qty, str(rate)]
                    )

                    cursor.execute(
                        """
                        INSERT INTO stock (order_master_idno, warehouse_code, product_code, issue, receive, date)
                        VALUES (%s, %s, %s, 0, %s, CURRENT_DATE)
                        """,
                        [om_idno, default_wh, product_code, qty]
                    )

            messages.success(request, f'Restock order {entry_no} created for {qty}× {prod_name}.')
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

    with connection.cursor() as cursor:
        cursor.execute("SELECT code, name FROM chart_of_account WHERE account_type = 'Supplier' ORDER BY code")
        suppliers = [{'code': r[0], 'name': r[1]} for r in cursor.fetchall()]

        cursor.execute("SELECT code, name FROM product ORDER BY code")
        products = [{'code': r[0], 'name': r[1]} for r in cursor.fetchall()]

    return render(request, 'admin_stock.html', {
        'stock_summary': stock_summary,
        'suppliers':     suppliers,
        'products':      products,
    })


@login_required(login_url='core:login')
@admin_required
def admin_reports_view(request):
    report_type = request.GET.get('report_type', '')
    start_date  = request.GET.get('start_date', '')
    end_date    = request.GET.get('end_date', '')

    results = []
    date_params = []
    date_clause = ''

    if start_date and end_date:
        date_clause = ' AND om.order_date BETWEEN %s AND %s'
        date_params = [start_date, end_date]

    if report_type == 'sales_master':
        sql = """
            SELECT om.entry_no, u.name, om.order_date,
                   SUM(od.qty * od.rate) AS total_amount
            FROM order_master om
            JOIN "user" u ON om.user_id = u.id
            JOIN order_detail od ON od.order_master_idno = om.idno
            WHERE om.order_type = 'Purchase Order'
        """ + date_clause + """
            GROUP BY om.idno, om.entry_no, u.name, om.order_date
            ORDER BY om.order_date DESC, om.idno DESC
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, date_params)
            results = [
                {'entry_no': r[0], 'customer_name': r[1], 'order_date': r[2], 'total_amount': r[3]}
                for r in cursor.fetchall()
            ]

    elif report_type == 'sales_detail':
        sql = """
            SELECT om.entry_no, om.order_date, p.name,
                   od.qty, od.rate, (od.qty * od.rate) AS line_total
            FROM order_detail od
            JOIN order_master om ON od.order_master_idno = om.idno
            JOIN product p ON od.product_code = p.code
            WHERE om.order_type = 'Purchase Order'
        """ + date_clause + """
            ORDER BY om.order_date DESC, om.idno DESC
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, date_params)
            results = [
                {'entry_no': r[0], 'order_date': r[1], 'product_name': r[2],
                 'qty': r[3], 'rate': r[4], 'line_total': r[5]}
                for r in cursor.fetchall()
            ]

    elif report_type == 'purchase_master':
        sql = """
            SELECT om.entry_no, coa.name AS supplier_name, om.order_date,
                   SUM(od.qty * od.rate) AS total_amount
            FROM order_master om
            JOIN "user" u ON om.user_id = u.id
            JOIN chart_of_account coa ON u.account_code = coa.code
            JOIN order_detail od ON od.order_master_idno = om.idno
            WHERE om.order_type = 'Restock Order'
        """ + date_clause + """
            GROUP BY om.idno, om.entry_no, coa.name, om.order_date
            ORDER BY om.order_date DESC, om.idno DESC
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, date_params)
            results = [
                {'entry_no': r[0], 'supplier_name': r[1], 'order_date': r[2], 'total_amount': r[3]}
                for r in cursor.fetchall()
            ]

    elif report_type == 'purchase_detail':
        sql = """
            SELECT om.entry_no, om.order_date, p.name,
                   od.qty, od.rate, (od.qty * od.rate) AS line_total
            FROM order_detail od
            JOIN order_master om ON od.order_master_idno = om.idno
            JOIN product p ON od.product_code = p.code
            WHERE om.order_type = 'Restock Order'
        """ + date_clause + """
            ORDER BY om.order_date DESC, om.idno DESC
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, date_params)
            results = [
                {'entry_no': r[0], 'order_date': r[1], 'product_name': r[2],
                 'qty': r[3], 'rate': r[4], 'line_total': r[5]}
                for r in cursor.fetchall()
            ]

    return render(request, 'admin_reports.html', {
        'report_type': report_type,
        'start_date':  start_date,
        'end_date':    end_date,
        'results':     results,
    })
