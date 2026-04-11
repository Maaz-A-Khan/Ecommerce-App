from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    user, chart_of_account, category, warehouse,
    product, order_master, order_detail, stock,
)


# ── user (extends AbstractUser → needs UserAdmin) ────────
@admin.register(user)
class userAdmin(UserAdmin):
    list_display  = ('username', 'name', 'role', 'is_staff')
    search_fields = ('username', 'name')
    ordering      = ('username',)

    fieldsets = UserAdmin.fieldsets + (
        ('User Info', {'fields': ('name', 'role', 'account_code')}),
    )


# ── chart_of_account ─────────────────────────────────────
@admin.register(chart_of_account)
class chartOfAccountAdmin(admin.ModelAdmin):
    list_display  = ('code', 'name', 'account_type')
    search_fields = ('code', 'name')


# ── category ─────────────────────────────────────────────
@admin.register(category)
class categoryAdmin(admin.ModelAdmin):
    list_display  = ('code', 'name')
    search_fields = ('code', 'name')


# ── warehouse ────────────────────────────────────────────
@admin.register(warehouse)
class warehouseAdmin(admin.ModelAdmin):
    list_display  = ('code', 'name')
    search_fields = ('code', 'name')


# ── product ──────────────────────────────────────────────
@admin.register(product)
class productAdmin(admin.ModelAdmin):
    list_display  = ('code', 'name', 'rate', 'category_code')
    search_fields = ('code', 'name')


# ── order_master ─────────────────────────────────────────
@admin.register(order_master)
class orderMasterAdmin(admin.ModelAdmin):
    list_display = ('idno', 'user', 'order_type',
                    'entry_no', 'order_date')


# ── order_detail ─────────────────────────────────────────
@admin.register(order_detail)
class orderDetailAdmin(admin.ModelAdmin):
    list_display = ('idno', 'order_master_idno', 'product_code',
                    'warehouse_code', 'qty', 'rate')


# ── stock ─────────────────────────────────────────────────
@admin.register(stock)
class stockAdmin(admin.ModelAdmin):
    list_display = ('idno', 'order_master_idno', 'warehouse_code',
                    'product_code', 'issue', 'receive', 'date')