from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Customer, Product, Stock, OrderMaster, OrderDetail

# Customer needs UserAdmin because it extends AbstractUser
@admin.register(Customer)
class CustomerAdmin(UserAdmin):
    # show these columns in the list view
    list_display  = ('Code', 'Name', 'Address', 'is_staff')
    # make Code searchable
    search_fields = ('Code', 'Name')
    ordering      = ('Code',)

    # add Code/Name/Address fields to the admin form
    fieldsets = UserAdmin.fieldsets + (
        ('Customer Info', {'fields': ('Code', 'Name', 'Address')}),
    )

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display  = ('Code', 'Name', 'Rate')
    search_fields = ('Code', 'Name')

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('Idno', 'Product', 'Qty')

@admin.register(OrderMaster)
class OrderMasterAdmin(admin.ModelAdmin):
    list_display = ('Idno', 'Entry_No', 'Customer', 'Order_Type')

@admin.register(OrderDetail)
class OrderDetailAdmin(admin.ModelAdmin):
    list_display  = ('Idno', 'order', 'Product', 'Qty', 'Rate', 'Amount')
    readonly_fields = ('Amount',)   # calculated automatically, not editable