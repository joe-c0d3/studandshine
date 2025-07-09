from django.db import models
from django.utils.text import slugify
from django.contrib.auth import settings
from decimal import Decimal
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
# Create your models here.


class Product(models.Model):
    CATEGORY = (("Electronics", "ELECTRONICS"),
                ("Groceries", "GROCERIES"),
                ("Clothings", "CLOTHINGS"),
                ("Wristwatch", "WRISTCHWATCH"),
                ("Anklet", "ANKLET"),
                ("Earrings", "EARRINGS"),
                ("Necklace", "NECKLACE"),
                ("Brooch", "BROOCH"),
                ("Bracelet", "BRACELET"),
                ("Bangle", "BANGLE")
                )
    name = models.CharField(max_length=100)
    slug = models.SlugField(blank=True, null=True)
    image = models.ImageField(upload_to="img")
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=15, choices=CATEGORY, blank=True, null=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):

        if not self.slug:
            self.slug = slugify(self.name)
            unique_slug = self.slug
            counter = 1
            if Product.objects.filter(slug=unique_slug).exists():
                unique_slug = f'{self.slug}={counter}'
                counter += 1
            self.slug = unique_slug

        super().save(*args, **kwargs)


class Cart(models.Model):
    cart_code = models.CharField(max_length=11, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, blank=True, null=True)
    paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    modified_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    def __str__(self):
        return self.cart_code


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} x {self.product.name} in cart {self.cart.id}"


class Transaction(models.Model):
    ref = models.CharField(max_length=255, unique=True)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='NGN')
    status = models.CharField(max_length=20, default='pending') # Can be pending, complete
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Transaction {self.ref} - {self.status}"


class Invoice(models.Model):
    ref = models.CharField(max_length=255, unique=True)  # Unique invoice reference
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, blank=True)  # Linked to the user
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)  # Linked to cart
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))  # Item total
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))  # Tax amount
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))  # Delivery fee
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))  # Final amount
    currency = models.CharField(max_length=10, default="NGN")  # Currency type
    status = models.CharField(max_length=20, choices=[("pending", "Pending"), ("paid", "Paid"), ("cancelled", "Cancelled")], default="pending")  # Payment status
    created_at = models.DateTimeField(auto_now_add=True)  # Timestamp for invoice creation
    updated_at = models.DateTimeField(auto_now=True)  # Timestamp for latest update

    def __str__(self):
        return f"Invoice {self.ref} - {self.user.username}"

