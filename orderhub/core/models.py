from django.db import models
from django.contrib.auth.models import AbstractUser

# ── Customer ──────────────────────────────────────────────
# Extends AbstractUser so Django's built-in login system works
# Code is the primary key (replaces the default integer id)
class Customer(AbstractUser):
    Code    = models.CharField(max_length=20, primary_key=True)
    Name    = models.CharField(max_length=100, blank=True)
    Address = models.TextField(blank=True)

    # AbstractUser already has username/password/email built in
    USERNAME_FIELD = 'Code'   # login with Code instead of username
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return f"{self.Code} - {self.Name}"


# ── Product ───────────────────────────────────────────────
class Product(models.Model):
    Code = models.CharField(max_length=10, primary_key=True)
    Name = models.CharField(max_length=100)
    Rate = models.DecimalField(max_digits=14, decimal_places=2)

    def __str__(self):
        return f"{self.Code} - {self.Name}"


# ── Stock ─────────────────────────────────────────────────
# Tracks how many units of each Product are available
class Stock(models.Model):
    Idno    = models.AutoField(primary_key=True)
    Product = models.ForeignKey(Product, on_delete=models.CASCADE)
    Qty     = models.IntegerField(default=0)

    def __str__(self):
        return f"Stock #{self.Idno} | {self.Product.Code} | Qty: {self.Qty}"


# ── OrderMaster ───────────────────────────────────────────
# One row per order placed — holds the header info
class OrderMaster(models.Model):
    Idno       = models.AutoField(primary_key=True)
    Entry_No   = models.CharField(max_length=20, unique=True)
    Customer   = models.ForeignKey(Customer, on_delete=models.CASCADE)
    Order_Type = models.CharField(max_length=50)

    def __str__(self):
        return f"Order {self.Entry_No} by {self.Customer.Code}"


# ── OrderDetail ───────────────────────────────────────────
# One row per product line inside an order
class OrderDetail(models.Model):
    Idno    = models.AutoField(primary_key=True)
    order   = models.ForeignKey(OrderMaster, on_delete=models.CASCADE)
    Product = models.ForeignKey(Product, on_delete=models.CASCADE)
    Qty     = models.IntegerField()
    Rate    = models.DecimalField(max_digits=14, decimal_places=2)
    Amount  = models.DecimalField(max_digits=14, decimal_places=2, editable=False)

    # Amount is AUTO-CALCULATED and STORED when the record is saved
    # Stored (not computed) so raw SQL reports can SUM it directly
    def save(self, *args, **kwargs):
        self.Amount = self.Qty * self.Rate
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Detail #{self.Idno} | {self.Product.Code} | {self.Qty} × {self.Rate}"