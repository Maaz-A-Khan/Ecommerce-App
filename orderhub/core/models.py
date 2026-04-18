from datetime import date
from django.db import models
from django.contrib.auth.models import AbstractUser


class region(models.Model):
    idno    = models.AutoField(primary_key=True)
    city    = models.CharField(max_length=100)
    country = models.CharField(max_length=100)

    class Meta:
        db_table = 'region'

    def __str__(self):
        return f"{self.city}, {self.country}"


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


class chart_of_account(models.Model):
    code         = models.CharField(max_length=20, primary_key=True)
    name         = models.CharField(max_length=100)
    account_type = models.CharField(max_length=50)
    region_idno  = models.ForeignKey(
        region, on_delete=models.SET_NULL,
        null=True, blank=True, db_column='region_idno'
    )

    class Meta:
        db_table = 'chart_of_account'

    def __str__(self):
        return f"{self.code} - {self.name}"


class category(models.Model):
    code = models.CharField(max_length=20, primary_key=True)
    name = models.CharField(max_length=100)

    class Meta:
        db_table = 'category'

    def __str__(self):
        return f"{self.code} - {self.name}"


class warehouse(models.Model):
    code = models.CharField(max_length=20, primary_key=True)
    name = models.CharField(max_length=100)

    class Meta:
        db_table = 'warehouse'

    def __str__(self):
        return f"{self.code} - {self.name}"


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


class product_bundle(models.Model):
    code                = models.CharField(max_length=20, primary_key=True)
    name                = models.CharField(max_length=100)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    is_active           = models.BooleanField(default=True)

    class Meta:
        db_table = 'product_bundle'

    def __str__(self):
        return f"{self.code} - {self.name}"


class bundle_item(models.Model):
    idno         = models.AutoField(primary_key=True)
    bundle_code  = models.ForeignKey(
        product_bundle, on_delete=models.CASCADE, db_column='bundle_code'
    )
    product_code = models.ForeignKey(
        product, on_delete=models.CASCADE, db_column='product_code'
    )
    qty_included = models.IntegerField()

    class Meta:
        db_table = 'bundle_item'

    def __str__(self):
        return f"Bundle {self.bundle_code_id} | {self.product_code_id} x{self.qty_included}"


class order_master(models.Model):
    idno       = models.AutoField(primary_key=True)
    user       = models.ForeignKey(
        user, on_delete=models.CASCADE, db_column='user_id'
    )
    order_type = models.CharField(max_length=50)
    entry_no   = models.CharField(max_length=20, unique=True)
    order_date = models.DateField(default=date.today, editable=False)

    class Meta:
        db_table = 'order_master'

    def __str__(self):
        return f"Order {self.entry_no} by {self.user}"


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
    rate              = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        db_table = 'order_detail'

    def __str__(self):
        return f"Detail #{self.idno} | {self.product_code} | {self.qty} x {self.rate}"


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