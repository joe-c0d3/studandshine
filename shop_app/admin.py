from django.contrib import admin
from .models import Product, Cart, CartItem, Invoice

# Register your models here.


admin.site.register([Product, Cart, CartItem, Invoice])
