import json
from decimal import Decimal
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from .models import user, product, order_master, order_detail, stock, warehouse


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
