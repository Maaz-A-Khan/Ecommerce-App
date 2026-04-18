from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # ── Public / Customer ────────────────────────────────
    path('',             views.login_view,          name='login'),
    path('logout/',      views.logout_view,         name='logout'),
    path('dashboard/',   views.dashboard_view,      name='dashboard'),
    path('products/',    views.product_list_view,   name='products'),
    path('checkout/',    views.order_checkout_view,  name='checkout'),
    path('register/',           views.register_view,               name='register'),
    path('my-orders/',          views.customer_dashboard_view,     name='customer_dashboard'),
    path('my-orders/<int:idno>/', views.customer_order_detail_view, name='customer_order_detail'),

    # ── Admin Panel ──────────────────────────────────────
    path('admin-panel/products/',          views.admin_products_view,      name='admin_products'),
    path('admin-panel/products/delete/<str:code>/', views.delete_product_view,  name='delete_product'),
    path('admin-panel/categories/delete/<str:code>/', views.delete_category_view, name='delete_category'),
    path('admin-panel/orders/',            views.admin_orders_view,        name='admin_orders'),
    path('admin-panel/orders/<int:idno>/', views.admin_order_detail_view,  name='admin_order_detail'),
    path('admin-panel/accounts/',          views.admin_accounts_view,      name='admin_accounts'),
    path('admin-panel/stock/',             views.admin_stock_view,         name='admin_stock'),
]
