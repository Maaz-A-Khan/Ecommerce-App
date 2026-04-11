from datetime import date
from django.db import models
from django.contrib.auth.models import AbstractUser


# ── user ──────────────────────────────────────────────────
# Extends AbstractUser so Django's built-in auth system works.
# Uses the default auto-incrementing id as PK and username for login.
class user(AbstractUser):
    name         = models.CharField(max_length=100, blank=True)
    role         = models.CharField(max_length=50, blank=True)
    account_code = models.ForeignKey(
        'chart_of_account', on_delete=models.SET_NULL,
        null=True, blank=True, db_column='account_code'
    )

    class Meta:
        db_table = 'user'

    def __str__(self):
        return f"{self.username} - {self.name}"


# ── chart_of_account ─────────────────────────────────────
class chart_of_account(models.Model):
    code         = models.CharField(max_length=20, primary_key=True)
    name         = models.CharField(max_length=100)
    account_type = models.CharField(max_length=50)

    class Meta:
        db_table = 'chart_of_account'

    def __str__(self):
        return f"{self.code} - {self.name}"


# ── category ─────────────────────────────────────────────
class category(models.Model):
    code = models.CharField(max_length=20, primary_key=True)
    name = models.CharField(max_length=100)

    class Meta:
        db_table = 'category'

    def __str__(self):
        return f"{self.code} - {self.name}"


# ── warehouse ────────────────────────────────────────────
class warehouse(models.Model):
    code = models.CharField(max_length=20, primary_key=True)
    name = models.CharField(max_length=100)

    class Meta:
        db_table = 'warehouse'

    def __str__(self):
        return f"{self.code} - {self.name}"


# ── product ──────────────────────────────────────────────
class product(models.Model):
    code          = models.CharField(max_length=20, primary_key=True)
    name          = models.CharField(max_length=100)
    rate          = models.DecimalField(max_digits=14, decimal_places=2)
    category_code = models.ForeignKey(
        category, on_delete=models.CASCADE, db_column='category_code'
    )

    class Meta:
        db_table = 'product'

    def __str__(self):
        return f"{self.code} - {self.name}"


# ── order_master ─────────────────────────────────────────
# One row per order placed — holds the header info.
# account_code is derived from user.account_code (no longer stored here).
# total_amount is computed from order_detail rows (no longer stored here).
class order_master(models.Model):
    idno         = models.AutoField(primary_key=True)
    user         = models.ForeignKey(
        user, on_delete=models.CASCADE, db_column='user_id'
    )
    order_type   = models.CharField(max_length=50)
    entry_no     = models.CharField(max_length=20, unique=True)
    order_date   = models.DateField(default=date.today, editable=False)

    class Meta:
        db_table = 'order_master'

    def __str__(self):
        return f"Order {self.entry_no} by {self.user}"


# ── order_detail ─────────────────────────────────────────
# One row per product line inside an order.
class order_detail(models.Model):
    idno              = models.AutoField(primary_key=True)
    order_master_idno = models.ForeignKey(
        order_master, on_delete=models.CASCADE, db_column='order_master_idno'
    )
    product_code      = models.ForeignKey(
        product, on_delete=models.CASCADE, db_column='product_code'
    )
    warehouse_code    = models.ForeignKey(
        warehouse, on_delete=models.CASCADE, db_column='warehouse_code'
    )
    qty               = models.IntegerField()
    # rate is intentionally denormalized from product.rate to preserve
    # the historical price at the time of purchase. If the product rate
    # changes later, existing order records will still reflect the
    # original price the customer paid.
    rate              = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        db_table = 'order_detail'

    def __str__(self):
        return f"Detail #{self.idno} | {self.product_code} | {self.qty} × {self.rate}"


# ── stock ─────────────────────────────────────────────────
# Tracks inventory movements per product/warehouse.
# 'issue' and 'receive' are tracked as separate fields.
# order_type and account_code are derived via order_master (not stored here).
class stock(models.Model):
    idno              = models.AutoField(primary_key=True)
    order_master_idno = models.ForeignKey(
        order_master, on_delete=models.CASCADE, db_column='order_master_idno'
    )
    warehouse_code    = models.ForeignKey(
        warehouse, on_delete=models.CASCADE, db_column='warehouse_code'
    )
    product_code      = models.ForeignKey(
        product, on_delete=models.CASCADE, db_column='product_code'
    )
    issue             = models.IntegerField(default=0)
    receive           = models.IntegerField(default=0)
    date              = models.DateField(default=date.today, editable=False)

    class Meta:
        db_table = 'stock'

    def __str__(self):
        return f"Stock #{self.idno} | {self.product_code} | Issue: {self.issue} | Receive: {self.receive}"