import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecoproject.settings')
django.setup()

from shops.models import Product

for p in Product.objects.all():
    print(f"Name: {p.name}")
    print(f"Slug: {p.slug}")
    print(f"URL: {p.get_absolute_url()}")
    print("-" * 20)
