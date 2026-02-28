from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages


# ── Login ─────────────────────────────────────────────────
def login_view(request):
    if request.method == 'POST':
        code     = request.POST.get('code')
        password = request.POST.get('password')
        user     = authenticate(request, username=code, password=password)
        if user is not None:
            login(request, user)
            return redirect('core:dashboard')
        else:
            messages.error(request, 'Invalid Code or Password.')
    return render(request, 'login.html')


# ── Logout ────────────────────────────────────────────────
def logout_view(request):
    logout(request)
    return redirect('core:login')


# ── Dashboard ─────────────────────────────────────────────
@login_required(login_url='core:login')
def dashboard_view(request):
    return render(request, 'dashboard.html')


# ── Product List ──────────────────────────────────────────
@login_required(login_url='core:login')
def product_list_view(request):
    # Phase 6 will populate this with Product.objects.all()
    context = {'products': []}
    return render(request, 'products.html', context)


# ── Order Checkout ────────────────────────────────────────
@login_required(login_url='core:login')
def order_checkout_view(request):
    # Phase 9 will implement full checkout logic with transaction.atomic()
    return render(request, 'checkout.html')
