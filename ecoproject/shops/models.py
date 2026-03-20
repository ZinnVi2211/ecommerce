from django.db import models
from django.urls import reverse

class Category(models.Model):
    name = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True)
    image_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True, verbose_name="Kích hoạt")

    class Meta:
        ordering = ('name',)
        verbose_name = 'category'
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name

class Product(models.Model):
    category = models.ForeignKey(Category,
                                 related_name='products',
                                 on_delete=models.CASCADE)
    name = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=200, db_index=True)
    image = models.ImageField(upload_to='products/',
                              blank=True)
    image_url = models.URLField(blank=True)
    description = models.TextField(blank=True)
    engine = models.CharField(max_length=50, blank=True)
    fuel_consumption = models.CharField(max_length=50, blank=True)
    color_options = models.JSONField(default=list, blank=True)
    version_options = models.JSONField(default=list, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=0)
    stock = models.PositiveIntegerField(default=0)
    available = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('name',)
        indexes = [
            models.Index(fields=['id', 'slug']),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('shops:motorcycle_detail',
                       args=[self.slug])


class Cart(models.Model):
    user = models.ForeignKey(
        'auth.User',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='carts'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'cart'
        verbose_name_plural = 'carts'

    def __str__(self):
        return f"Cart #{self.id} - {self.user or 'Guest'}"

    def total_price(self):
        return sum(item.subtotal for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='cart_items'
    )
    quantity = models.PositiveIntegerField(default=1)
    selected_config = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ('cart', 'product')
        verbose_name = 'cart item'
        verbose_name_plural = 'cart items'

    def __str__(self):
        return f"{self.product.name} x{self.quantity}"

    @property
    def subtotal(self):
        return self.product.price * self.quantity


class Voucher(models.Model):
    code = models.CharField(max_length=50, unique=True)
    discount_percent = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)
    expiry_date = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = 'voucher'
        verbose_name_plural = 'vouchers'

    def __str__(self):
        return self.code

    def is_valid(self):
        from django.utils import timezone
        from datetime import date

        if not self.active:
            return False
        if self.expiry_date and self.expiry_date < date.today():
            return False
        return True


class Order(models.Model):
    PAYMENT_TYPE_CHOICES = [
        ('deposit', 'Deposit 10%'),
        ('full', 'Full Payment'),
        ('showroom', 'Pay at Showroom'),
        ('bank_transfer', 'Bank Transfer'),
    ]
    PAYMENT_STATUS_CHOICES = [
        ('unpaid', 'Unpaid'),
        ('partial', 'Partial'),
        ('paid', 'Paid'),
        ('pending_confirmation', 'Pending Confirmation'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ]

    user = models.ForeignKey(
        'auth.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='orders'
    )
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    address = models.TextField()
    city = models.CharField(max_length=100)
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES)
    payment_status = models.CharField(max_length=30, choices=PAYMENT_STATUS_CHOICES, default='unpaid')
    total_price = models.DecimalField(max_digits=12, decimal_places=0)
    deposit_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    remaining_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    voucher = models.ForeignKey(Voucher, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'order'
        verbose_name_plural = 'orders'

    def __str__(self):
        return f"Order #{self.id} - {self.full_name} ({self.status})"

    @property
    def discount_amount(self):
        if self.voucher and self.voucher.is_valid():
            return self.total_price * (self.voucher.discount_percent / 100)
        return 0


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    price = models.DecimalField(max_digits=12, decimal_places=0)
    quantity = models.PositiveIntegerField()
    config = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = 'order item'
        verbose_name_plural = 'order items'

    def __str__(self):
        return f"{self.product.name if self.product else 'Deleted product'} x{self.quantity}"

    @property
    def subtotal(self):
        return self.price * self.quantity
