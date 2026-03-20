import os
import django
import csv

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecoproject.settings')
django.setup()

from shops.models import Product

with open('products_debug.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['ID', 'Name', 'Slug', 'URL'])
    for p in Product.objects.all():
        writer.writerow([p.id, p.name, p.slug, p.get_absolute_url()])

print("Generated products_debug.csv")
