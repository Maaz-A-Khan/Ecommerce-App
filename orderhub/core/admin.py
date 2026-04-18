from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    user, chart_of_account, category, warehouse,
    product, order_master, order_detail, stock,
    region, product_bundle, bundle_item,
)


@admin.register(user)
class userAdmin(UserAdmin):
    list_display  = ('username', 'name', 'role', 'is_staff')
    search_fields = ('username', 'name')
    ordering      = ('username',)

    fieldsets = UserAdmin.fieldsets + (
        ('User Info', {'fields': ('name', 'role', 'account_code')}),
    )


@admin.register(chart_of_account)
class chartOfAccountAdmin(admin.ModelAdmin):
    list_display  = ('code', 'name', 'account_type', 'region_idno')
    search_fields = ('code', 'name')


@admin.register(category)
class categoryAdmin(admin.ModelAdmin):
    list_display  = ('code', 'name')
    search_fields = ('code', 'name')


@admin.register(warehouse)
class warehouseAdmin(admin.ModelAdmin):
    list_display  = ('code', 'name')
    search_fields = ('code', 'name')


@admin.register(product)
class productAdmin(admin.ModelAdmin):
    list_display  = ('code', 'name', 'rate', 'category_code')
    search_fields = ('code', 'name')


@admin.register(order_master)
class orderMasterAdmin(admin.ModelAdmin):
    list_display = ('idno', 'user', 'order_type', 'entry_no', 'order_date')


@admin.register(order_detail)
class orderDetailAdmin(admin.ModelAdmin):
    list_display = ('idno', 'order_master_idno', 'product_code',
                    'warehouse_code', 'qty', 'rate')


@admin.register(stock)
class stockAdmin(admin.ModelAdmin):
    list_display = ('idno', 'order_master_idno', 'warehouse_code',
                    'product_code', 'issue', 'receive', 'date')


@admin.register(region)
class regionAdmin(admin.ModelAdmin):
    list_display  = ('idno', 'city', 'country')
    search_fields = ('city', 'country')


@admin.register(product_bundle)
class productBundleAdmin(admin.ModelAdmin):
    list_display  = ('code', 'name', 'discount_percentage', 'is_active')
    search_fields = ('code', 'name')


@admin.register(bundle_item)
class bundleItemAdmin(admin.ModelAdmin):
    list_display  = ('idno', 'bundle_code', 'product_code', 'qty_included')
    search_fields = ('bundle_code__code', 'product_code__code')