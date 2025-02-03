from django.db import models
from django.contrib.auth.models import User


class Warehouse(models.Model):
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    users = models.ManyToManyField(User, related_name="warehouses", blank=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    PRODUCT_TYPE_CHOICES = [
        ('electronics', 'Electronics'),
        ('clothing', 'Clothing'),
        ('food', 'Food'),
        ('furniture', 'Furniture'),
        # Add more product types as needed
    ]
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=100, unique=True)
    barcode = models.CharField(max_length=100, unique=True)
    product_type = models.CharField(max_length=50, choices=PRODUCT_TYPE_CHOICES)
    description = models.TextField()
    quantity_in_stock = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    unit_of_measure = models.CharField(max_length=50)  # e.g., kg, liters, pieces
    expiry_date = models.DateField(null=True, blank=True)
    manufacturer_name = models.CharField(max_length=255)
    supplier_details = models.TextField()
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
