from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, DetailView
from django.http import Http404, JsonResponse, HttpResponse, HttpResponseForbidden
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum, Count, Value, DecimalField
from django.db.models.functions import TruncDate, Coalesce
from django.utils import timezone
from django.urls import reverse
from datetime import timedelta, datetime
from io import BytesIO
import json
import csv
import xml.etree.ElementTree as ET

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.graphics.shapes import Drawing, Circle, String
from reportlab.graphics.barcode.qr import QrCodeWidget

from .models import (
    Cart,
    CartItem,
    Category,
    Notification,
    Order,
    OrderItem,
    Product,
    ReturnRequest,
    Voucher,
    Wishlist,
)
from .forms import ProductForm, CategoryForm, CheckoutForm, OrderStatusForm


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _notification_to_dict(notification):
    return {
        'id': notification.id,
        'title': notification.title,
        'message': notification.message,
        'type': notification.type,
        'is_read': notification.is_read,
        'link': notification.link,
        'created_at': timezone.localtime(notification.created_at).strftime('%Y-%m-%d %H:%M'),
        'read_url': reverse('shops:notification_read', args=[notification.id]),
    }



def index(request):
    products = Product.objects.filter(available=True).order_by('-created')[:8]
    return render(request, 'shops/index.html', {'products': products})

def product_list(request, category_slug=None):
    category = None
    if request.user.is_staff:
        categories = Category.objects.all()
        products = Product.objects.all()
    else:
        categories = Category.objects.filter(is_active=True)
        products = Product.objects.filter(available=True, category__is_active=True)
        
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        if not request.user.is_staff and not category.is_active:
            products = products.none()
        products = products.filter(category=category)
    return render(request, 'shops/products.html', {
        'category': category,
        'categories': categories,
        'products': products
    })


class MotorcycleListView(ListView):
    template_name = 'shops/motorcycle_list.html'
    context_object_name = 'products'

    def get_queryset(self):
        qs = Product.objects.filter(available=True, category__slug='motorcycles', category__is_active=True)

        q = self.request.GET.get('q', '').strip()
        engine = self.request.GET.get('engine', '').strip()
        min_price = self.request.GET.get('min_price', '').strip()
        max_price = self.request.GET.get('max_price', '').strip()

        if q:
            qs = qs.filter(name__icontains=q)
        if engine:
            qs = qs.filter(engine__iexact=engine)
        if min_price:
            try:
                qs = qs.filter(price__gte=int(min_price))
            except ValueError:
                pass
        if max_price:
            try:
                qs = qs.filter(price__lte=int(max_price))
            except ValueError:
                pass

        return qs.order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        engines = (Product.objects.filter(available=True, category__slug='motorcycles')
                   .exclude(engine='')
                   .values_list('engine', flat=True)
                   .distinct()
                   .order_by('engine'))
        context['engines'] = engines
        context['filters'] = {
            'q': self.request.GET.get('q', '').strip(),
            'engine': self.request.GET.get('engine', '').strip(),
            'min_price': self.request.GET.get('min_price', '').strip(),
            'max_price': self.request.GET.get('max_price', '').strip(),
        }
        return context


class MotorcycleDetailView(DetailView):
    template_name = 'shops/motorcycle_detail.html'
    context_object_name = 'product'

    def get_object(self, queryset=None):
        slug = self.kwargs.get('slug')
        product = (Product.objects
                   .filter(slug=slug, available=True, category__slug='motorcycles')
                   .select_related('category')
                   .first())
        if not product:
            raise Http404('Motorcycle not found')
        return product

@staff_member_required
def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            messages.success(request, f'Sản phẩm "{product.name}" đã được thêm thành công!')
            return redirect('shops:product_list')
    else:
        form = ProductForm()
    return render(request, 'shops/product_form.html', {'form': form, 'title': 'Thêm sản phẩm mới'})

@staff_member_required
def product_update(request, id):
    product = get_object_or_404(Product, id=id)
    if request.method == 'POST':
        old_price = product.price
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            updated_product = form.save()
            if updated_product.price < old_price and updated_product.available:
                wishlist_user_ids = Wishlist.objects.filter(product=updated_product).values_list('user_id', flat=True)
                notifications = [
                    Notification(
                        user_id=user_id,
                        title='Gi?m gi? s?n ph?m y?u th?ch',
                        message=f'S?n ph?m "{updated_product.name}" v?a gi?m gi?. Xem ngay!',
                        type='wishlist',
                        link=updated_product.get_absolute_url()
                    )
                    for user_id in wishlist_user_ids
                ]
                if notifications:
                    Notification.objects.bulk_create(notifications)
            messages.success(request, f'S?n ph?m "{product.name}" ?? ???c c?p nh?t!')
            return redirect('shops:product_list')
    else:
        form = ProductForm(instance=product)
    return render(request, 'shops/product_form.html', {'form': form, 'title': 'C?p nh?t s?n ph?m', 'product': product})

@staff_member_required
def product_delete(request, id):
    product = get_object_or_404(Product, id=id)
    if request.method == 'POST':
        product_name = product.name
        product.delete()
        messages.success(request, f'Sản phẩm "{product_name}" đã bị xóa!')
        return redirect('shops:product_list')
    return render(request, 'shops/product_confirm_delete.html', {'product': product})

@staff_member_required
def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Danh mục "{category.name}" đã được thêm thành công!')
            return redirect('shops:product_list')
    else:
        form = CategoryForm()
    return render(request, 'shops/category_form.html', {'form': form, 'title': 'Thêm danh mục mới'})

@staff_member_required
def category_update(request, id):
    category = get_object_or_404(Category, id=id)
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f'Danh mục "{category.name}" đã được cập nhật!')
            return redirect('shops:product_list')
    else:
        form = CategoryForm(instance=category)
    return render(request, 'shops/category_form.html', {'form': form, 'title': 'Cập nhật danh mục', 'category': category})

@staff_member_required
def category_delete(request, id):
    category = get_object_or_404(Category, id=id)
    if request.method == 'POST':
        category_name = category.name
        category.delete()
        messages.success(request, f'Danh mục "{category_name}" và toàn bộ sản phẩm bên trong đã bị xóa!')
        return redirect('shops:product_list')
    return render(request, 'shops/category_confirm_delete.html', {'category': category})


def _get_or_create_cart(request):
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
        if created and 'cart_id' in request.session:
            try:
                old = Cart.objects.get(id=request.session['cart_id'])
                old_items = old.items.all()
                for item in old_items:
                    existing, _ = CartItem.objects.get_or_create(cart=cart, product=item.product, defaults={'quantity': item.quantity, 'selected_config': item.selected_config})
                    if not _:
                        existing.quantity += item.quantity
                        existing.save()
                old.delete()
            except Cart.DoesNotExist:
                pass
        return cart

    cart_id = request.session.get('cart_id')
    if cart_id:
        cart = Cart.objects.filter(id=cart_id).first()
        if cart:
            return cart

    cart = Cart.objects.create()
    request.session['cart_id'] = cart.id
    return cart


def cart_view(request):
    cart = _get_or_create_cart(request)
    items = cart.items.select_related('product').all()

    subtotal = cart.total_price()
    total = subtotal

    return render(request, 'shops/cart.html', {
        'cart': cart,
        'items': items,
        'subtotal': subtotal,
        'total': total,
    })


def add_to_cart(request, id):
    product = get_object_or_404(Product, id=id, available=True)
    if request.method == 'POST':
        try:
            quantity = int(request.POST.get('quantity', 1))
        except ValueError:
            quantity = 1
        selected_config = {
            'color': request.POST.get('color', 'default'),
            'version': request.POST.get('version', 'standard')
        }
    else:
        quantity = int(request.GET.get('quantity', 1))
        selected_config = {
            'color': request.GET.get('color', 'default'),
            'version': request.GET.get('version', 'standard')
        }

    if quantity <= 0:
        messages.error(request, 'Số lượng phải lớn hơn 0.')
        return redirect('shops:product_list')

    cart = _get_or_create_cart(request)
    item, created = CartItem.objects.get_or_create(cart=cart, product=product, defaults={'quantity': quantity, 'selected_config': selected_config})
    if not created:
        item.quantity += quantity
        item.selected_config = selected_config
        item.save()
    messages.success(request, f'Đã thêm {product.name} vào giỏ hàng.')
    return redirect('shops:cart_view')


def remove_from_cart(request, id):
    cart = _get_or_create_cart(request)
    item = get_object_or_404(CartItem, id=id, cart=cart)
    item.delete()
    messages.success(request, 'Đã xóa mục khỏi giỏ hàng.')
    return redirect('shops:cart_view')


def update_cart_item(request, id):
    if request.method != 'POST':
        return redirect('shops:cart_view')

    cart = _get_or_create_cart(request)
    item = get_object_or_404(CartItem, id=id, cart=cart)
    quantity = request.POST.get('quantity')
    try:
        quantity = int(quantity)
        if quantity < 1:
            item.delete()
            messages.success(request, 'Đã xóa mục khỏi giỏ hàng do số lượng bằng 0.')
        else:
            if quantity > item.product.stock:
                messages.warning(request, 'Số lượng vượt quá tồn kho, đã điều chỉnh tối đa.')
                quantity = item.product.stock
            item.quantity = quantity
            item.save()
            messages.success(request, 'Cập nhật giỏ hàng thành công.')
    except (ValueError, TypeError):
        messages.error(request, 'Số lượng không hợp lệ.')

    return redirect('shops:cart_view')




def checkout_view(request):
    cart = _get_or_create_cart(request)
    buy_now = request.session.get('buy_now')

    if buy_now:
        product = Product.objects.filter(id=buy_now.get('product_id'), available=True).first()
        if not product:
            request.session.pop('buy_now', None)
            messages.error(request, 'Sản phẩm không còn tồn tại. Vui lòng chọn lại.')
            return redirect('shops:product_list')
        items = [{
            'product': product,
            'quantity': int(buy_now.get('quantity', 1)),
            'selected_config': buy_now.get('selected_config', {}),
            'subtotal': product.price * int(buy_now.get('quantity', 1))
        }]
    else:
        items = list(cart.items.select_related('product').all())
        if not items:
            messages.error(request, 'Giỏ hàng trống. Vui lòng thêm sản phẩm trước khi thanh toán.')
            return redirect('shops:cart_view')


    subtotal = cart.total_price()
    total = subtotal

    if request.method == 'POST':
        return place_order(request)

    else:
        initial = {}
        if request.user.is_authenticated:
            user = request.user
            initial['full_name'] = f"{user.first_name} {user.last_name}".strip() or user.username
            initial['email'] = user.email
        form = CheckoutForm(initial=initial)

    return render(request, 'shops/checkout.html', {
        'form': form,
        'items': items,
        'subtotal': subtotal,
        'total': total,
        'buy_now': bool(buy_now),
    })


def place_order(request):
    cart = _get_or_create_cart(request)
    buy_now = request.session.get('buy_now')

    if request.session.get('order_submitted'):
        messages.info(request, 'Đơn hàng đã được gửi. Không thể gửi lại.')
        return redirect('shops:order_success')

    form = CheckoutForm(request.POST)
    if not form.is_valid():
        messages.error(request, 'Vui lòng kiểm tra lại thông tin thanh toán.')
        return redirect('shops:checkout_view')

    with transaction.atomic():
        if buy_now:
            product = Product.objects.select_for_update().filter(id=buy_now.get('product_id'), available=True).first()
            if not product:
                request.session.pop('buy_now', None)
                messages.error(request, 'Sản phẩm không còn tồn tại. Vui lòng chọn lại.')
                return redirect('shops:product_list')

            quantity = int(buy_now.get('quantity', 1))
            if quantity < 1:
                messages.error(request, 'Số lượng không hợp lệ.')
                return redirect('shops:product_list')
            if quantity > product.stock:
                messages.error(request, f'Sản phẩm "{product.name}" không đủ tồn kho.')
                return redirect('shops:product_list')

            selected_config = buy_now.get('selected_config', {})
            subtotal = product.price * quantity
        else:
            cart_items = CartItem.objects.select_related('product').select_for_update().filter(cart=cart)
            if not cart_items.exists():
                messages.error(request, 'Giỏ hàng trống. Vui lòng thêm sản phẩm trước khi thanh toán.')
                return redirect('shops:cart_view')

            for item in cart_items:
                if item.quantity > item.product.stock:
                    messages.error(request, f'Sản phẩm "{item.product.name}" không đủ tồn kho.')
                    return redirect('shops:cart_view')

            subtotal = sum((item.product.price * item.quantity) for item in cart_items)

        voucher = None
        discount_value = 0
        voucher_code = request.session.get('voucher_code')
        if voucher_code:
            voucher = Voucher.objects.filter(code__iexact=voucher_code).first()
            if voucher and voucher.is_valid():
                discount_value = (subtotal * voucher.discount_percent) / 100
            else:
                voucher = None
                request.session.pop('voucher_code', None)

        total = round(subtotal - discount_value)
        payment_type = form.cleaned_data['payment_type']

        if payment_type == 'deposit':
            deposit = round(total * 0.1)
            remaining = total - deposit
            payment_status = 'partial'
        elif payment_type == 'full':
            deposit = total
            remaining = 0
            payment_status = 'paid'
        elif payment_type == 'showroom':
            deposit = 0
            remaining = total
            payment_status = 'unpaid'
        else:
            deposit = total
            remaining = 0
            payment_status = 'pending_confirmation'

        order = Order.objects.create(
            user=request.user if request.user.is_authenticated else None,
            full_name=form.cleaned_data['full_name'],
            phone=form.cleaned_data['phone'],
            email=form.cleaned_data['email'],
            address=form.cleaned_data['address'],
            city=form.cleaned_data['city'],
            payment_type=payment_type,
            payment_status=payment_status,
            total_price=total,
            deposit_amount=deposit,
            remaining_amount=remaining,
            voucher=voucher,
            status='pending'
        )

        if buy_now:
            OrderItem.objects.create(
                order=order,
                product=product,
                price=product.price,
                quantity=quantity,
                config=selected_config or {}
            )
            product.stock = max(product.stock - quantity, 0)
            product.save()
        else:
            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    price=item.product.price,
                    quantity=item.quantity,
                    config=item.selected_config or {}
                )
                item.product.stock = max(item.product.stock - item.quantity, 0)
                item.product.save()

        if buy_now:
            request.session.pop('buy_now', None)
        else:
            cart_items.delete()
        request.session.pop('voucher_code', None)
        request.session['order_submitted'] = True
        request.session['last_order_id'] = order.id
        request.session.modified = True

        messages.success(request, 'Đặt hàng thành công. Nhân viên sẽ liên hệ trong 24 giờ.')
        return redirect('shops:order_success')


def order_success(request):
    order_id = request.session.get('last_order_id')
    order = None
    if order_id:
        order = Order.objects.filter(id=order_id).first()

    if not order:
        messages.info(request, 'Không tìm thấy đơn hàng vừa hoàn tất.')
        return redirect('shops:product_list')

    # one-time view guarantee
    request.session.pop('order_submitted', None)

    return render(request, 'shops/success.html', {
        'order': order,
    })


def order_status(request):
    form = OrderStatusForm(request.POST or None)
    order = None

    if request.method == 'POST' and form.is_valid():
        order_id = form.cleaned_data['order_id']
        key = form.cleaned_data['phone_or_email'].strip()
        order = Order.objects.filter(id=order_id).first()
        if not order:
            messages.error(request, 'Không tìm thấy đơn hàng. Vui lòng kiểm tra lại mã đơn.')
        else:
            phone_match = key == order.phone
            email_match = key.lower() == order.email.lower()
            if not (phone_match or email_match):
                order = None
                messages.error(request, 'Thông tin xác thực không khớp. Vui lòng thử lại.')

    return render(request, 'shops/order_status.html', {
        'form': form,
        'order': order,
    })


@login_required
def toggle_wishlist(request, product_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    product = Product.objects.filter(id=product_id).first()
    if not product:
        return JsonResponse({'error': 'Product not found'}, status=404)

    wishlist_item = Wishlist.objects.filter(user=request.user, product=product).first()
    if wishlist_item:
        wishlist_item.delete()
        status = 'removed'
    else:
        Wishlist.objects.get_or_create(user=request.user, product=product)
        status = 'added'

    wishlist_count = Wishlist.objects.filter(user=request.user).count()
    return JsonResponse({'status': status, 'wishlist_count': wishlist_count})


@login_required
def wishlist_view(request):
    wishlist_items = (Wishlist.objects
                      .filter(user=request.user, product__available=True)
                      .select_related('product')
                      .order_by('-created_at'))
    return render(request, 'shops/wishlist.html', {
        'wishlist_items': wishlist_items,
    })


@login_required
def notification_list_view(request):
    try:
        page = int(request.GET.get('page', 1) or 1)
    except ValueError:
        page = 1
    page_size = 10
    qs = Notification.objects.filter(user=request.user).order_by('-created_at')
    total = qs.count()
    start = (page - 1) * page_size
    end = start + page_size
    notifications = list(qs[start:end])
    has_next = total > end

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'notifications': [_notification_to_dict(n) for n in notifications],
            'has_next': has_next,
            'unread_count': Notification.objects.filter(user=request.user, is_read=False).count(),
        })

    return render(request, 'shops/notifications.html', {
        'notifications': notifications,
        'has_next': has_next,
    })


@login_required
def notification_dropdown_api(request):
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:5]
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({
        'notifications': [_notification_to_dict(n) for n in notifications],
        'unread_count': unread_count,
    })


@login_required
def mark_as_read(request, id):
    notification = get_object_or_404(Notification, id=id, user=request.user)
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=['is_read'])

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'ok'})

    next_url = request.GET.get('next') or notification.link or reverse('shops:notification_list')
    return redirect(next_url)


@login_required
def mark_all_as_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'ok'})
    return redirect('shops:notification_list')


@staff_member_required
def admin_dashboard_view(request):
    today = timezone.localdate()
    paid_orders = Order.objects.filter(payment_status='paid')
    zero_decimal = Value(0, output_field=DecimalField(max_digits=12, decimal_places=0))

    total_revenue = paid_orders.aggregate(total=Coalesce(Sum('total_price'), zero_decimal))['total']
    today_revenue = paid_orders.filter(created_at__date=today).aggregate(total=Coalesce(Sum('total_price'), zero_decimal))['total']
    monthly_revenue = paid_orders.filter(
        created_at__year=today.year,
        created_at__month=today.month
    ).aggregate(total=Coalesce(Sum('total_price'), zero_decimal))['total']

    start_date = _parse_date(request.GET.get('start_date'))
    end_date = _parse_date(request.GET.get('end_date'))
    if start_date and end_date and start_date > end_date:
        start_date, end_date = end_date, start_date

    orders_range_qs = Order.objects.all()
    if start_date and end_date:
        orders_range_qs = orders_range_qs.filter(created_at__date__range=(start_date, end_date))
    elif start_date:
        orders_range_qs = orders_range_qs.filter(created_at__date__gte=start_date)
    elif end_date:
        orders_range_qs = orders_range_qs.filter(created_at__date__lte=end_date)

    if request.GET.get('export') == 'orders':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="orders_export.csv"'
        writer = csv.writer(response)
        writer.writerow(['Order ID', 'Customer', 'Payment Type', 'Payment Status', 'Total', 'Created At'])
        for order in orders_range_qs.order_by('-created_at'):
            writer.writerow([
                order.id,
                order.full_name,
                order.get_payment_type_display(),
                order.get_payment_status_display(),
                order.total_price,
                order.created_at.strftime('%Y-%m-%d %H:%M')
            ])
        return response

    orders_count = orders_range_qs.count()
    products_sold = OrderItem.objects.filter(order__in=orders_range_qs).aggregate(
        total=Coalesce(Sum('quantity'), 0)
    )['total']

    best_sellers = (OrderItem.objects
                    .filter(order__in=orders_range_qs)
                    .values('product__id', 'product__name')
                    .annotate(total_qty=Coalesce(Sum('quantity'), 0))
                    .order_by('-total_qty', 'product__name')[:5])

    top_favorites = (Wishlist.objects
                     .values('product__id', 'product__name')
                     .annotate(fav_count=Count('id'))
                     .order_by('-fav_count', 'product__name')[:5])

    low_stock_products = Product.objects.filter(stock__lt=5).order_by('stock', 'name')
    low_stock_count = low_stock_products.count()

    payment_stats = {
        'deposit_count': orders_range_qs.filter(payment_type='deposit').count(),
        'full_count': orders_range_qs.filter(payment_type='full').count(),
        'showroom_count': orders_range_qs.filter(payment_type='showroom').count(),
    }

    recent_orders = (orders_range_qs
                     .select_related('user')
                     .order_by('-created_at')[:10])

    start_7 = today - timedelta(days=6)
    daily_revenue = (paid_orders
                     .filter(created_at__date__range=(start_7, today))
                     .annotate(day=TruncDate('created_at'))
                     .values('day')
                     .annotate(total=Coalesce(Sum('total_price'), zero_decimal))
                     .order_by('day'))
    daily_map = {row['day']: row['total'] for row in daily_revenue}

    revenue_chart_labels = []
    revenue_chart_values = []
    for i in range(7):
        day = start_7 + timedelta(days=i)
        revenue_chart_labels.append(day.strftime('%d/%m'))
        revenue_chart_values.append(float(daily_map.get(day, 0)))

    payment_chart_labels = ['Đặt cọc', 'Thanh toán đủ', 'Tại showroom']
    payment_chart_values = [
        payment_stats['deposit_count'],
        payment_stats['full_count'],
        payment_stats['showroom_count'],
    ]

    notifications = {
        'pending_orders': orders_range_qs.filter(status='pending').count(),
        'unpaid_orders': orders_range_qs.filter(payment_status='unpaid').count(),
        'low_stock': low_stock_count,
    }

    context = {
        'total_revenue': total_revenue,
        'today_revenue': today_revenue,
        'monthly_revenue': monthly_revenue,
        'orders_count': orders_count,
        'products_sold': products_sold,
        'best_sellers': best_sellers,
        'top_favorites': top_favorites,
        'low_stock_products': low_stock_products,
        'low_stock_count': low_stock_count,
        'payment_stats': payment_stats,
        'recent_orders': recent_orders,
        'revenue_chart_labels': json.dumps(revenue_chart_labels),
        'revenue_chart_values': json.dumps(revenue_chart_values),
        'payment_chart_labels': json.dumps(payment_chart_labels),
        'payment_chart_values': json.dumps(payment_chart_values),
        'start_date': start_date.isoformat() if start_date else '',
        'end_date': end_date.isoformat() if end_date else '',
        'date_range_active': bool(start_date or end_date),
        'notifications': notifications,
    }
    return render(request, 'shops/dashboard.html', context)


@staff_member_required
def dashboard_api(request):
    today = timezone.localdate()
    start_7 = today - timedelta(days=6)
    paid_orders = Order.objects.filter(payment_status='paid')
    zero_decimal = Value(0, output_field=DecimalField(max_digits=12, decimal_places=0))

    daily_revenue = (paid_orders
                     .filter(created_at__date__range=(start_7, today))
                     .annotate(day=TruncDate('created_at'))
                     .values('day')
                     .annotate(total=Coalesce(Sum('total_price'), zero_decimal))
                     .order_by('day'))
    daily_map = {row['day']: row['total'] for row in daily_revenue}
    revenue_data = []
    for i in range(7):
        day = start_7 + timedelta(days=i)
        revenue_data.append({
            'date': day.isoformat(),
            'total': float(daily_map.get(day, 0)),
        })

    orders_qs = Order.objects.all()
    payment_stats = {
        'deposit': orders_qs.filter(payment_type='deposit').count(),
        'full': orders_qs.filter(payment_type='full').count(),
        'showroom': orders_qs.filter(payment_type='showroom').count(),
    }

    return JsonResponse({
        'revenue_data': revenue_data,
        'payment_stats': payment_stats,
    })


def product_detail_view(request, slug):
    product = get_object_or_404(Product, slug=slug, available=True)
    colors = product.color_options or []
    versions = product.version_options or []

    if request.method == 'POST':
        try:
            quantity = int(request.POST.get('quantity', 1))
        except ValueError:
            quantity = 1

        selected_color = request.POST.get('color') or (colors[0] if colors else 'Default')
        selected_version = request.POST.get('version') or (versions[0] if versions else 'Standard')

        if colors and selected_color not in colors:
            messages.error(request, 'Màu sắc không hợp lệ.')
            return redirect('shops:product_detail', slug=product.slug)
        if versions and selected_version not in versions:
            messages.error(request, 'Phiên bản không hợp lệ.')
            return redirect('shops:product_detail', slug=product.slug)
        if quantity < 1:
            messages.error(request, 'Số lượng không hợp lệ.')
            return redirect('shops:product_detail', slug=product.slug)
        if quantity > product.stock:
            messages.error(request, 'Số lượng vượt quá tồn kho.')
            return redirect('shops:product_detail', slug=product.slug)

        selected_config = {'color': selected_color, 'version': selected_version}

        if 'buy_now' in request.POST:
            request.session['buy_now'] = {
                'product_id': product.id,
                'quantity': quantity,
                'selected_config': selected_config
            }
            request.session.modified = True
            return redirect('shops:checkout_view')

        cart = _get_or_create_cart(request)
        item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity, 'selected_config': selected_config}
        )
        if not created:
            item.quantity = min(item.quantity + quantity, product.stock)
            item.selected_config = selected_config
            item.save()

        messages.success(request, 'Đã thêm sản phẩm vào giỏ hàng.')
        return redirect('shops:cart_view')

    related_products = (Product.objects
                        .filter(category=product.category, available=True)
                        .exclude(id=product.id)[:4])

    return render(request, 'shops/product_detail.html', {
        'product': product,
        'colors': colors,
        'versions': versions,
        'related_products': related_products
    })

@login_required
def order_history(request):
    if request.user.is_staff:
        orders = Order.objects.all().order_by('-created_at')
    else:
        orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    return render(request, 'shops/order_history.html', {'orders': orders})

@login_required
def order_detail(request, pk):
    if request.user.is_staff:
        order = get_object_or_404(Order, pk=pk)
    else:
        order = get_object_or_404(Order, pk=pk, user=request.user)
    
    items = order.items.select_related('product').all()
    # For admin status form
    status_choices = Order.STATUS_CHOICES
    
    return render(request, 'shops/order_detail.html', {
        'order': order,
        'items': items,
        'status_choices': status_choices
    })

@login_required
def order_cancel(request, pk):
    if request.method == 'POST':
        order = get_object_or_404(Order, pk=pk, user=request.user)
        if order.can_cancel:
            order.status = 'cancelled'
            order.save()
            messages.success(request, f'Đơn hàng #{order.id} đã được hủy thành công.')
        else:
            messages.error(request, 'Không thể hủy đơn hàng này.')
    return redirect('shops:order_detail', pk=pk)


def _order_access_allowed(user, order):
    if not user.is_authenticated:
        return False
    if user.is_staff:
        return True
    if order.user_id:
        return order.user_id == user.id
    return False


def _invoice_number(order):
    return f"INV-{order.created_at:%Y}-{order.id:04d}"


def export_order_pdf(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if not _order_access_allowed(request.user, order):
        return HttpResponseForbidden('Access denied')

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=24,
        leftMargin=24,
        topMargin=24,
        bottomMargin=24
    )
    styles = getSampleStyleSheet()
    story = []

    logo = Drawing(36 * mm, 18 * mm)
    logo.add(Circle(9 * mm, 9 * mm, 8 * mm, fillColor=colors.red, strokeColor=colors.red))
    logo.add(String(9 * mm, 6 * mm, 'M', textAnchor='middle', fillColor=colors.white, fontSize=12))

    story.append(logo)
    story.append(Paragraph('<b>DEMO MOTOR SHOP</b>', styles['Title']))
    story.append(Paragraph(f'Order Export - {_invoice_number(order)}', styles['Heading2']))
    story.append(Spacer(1, 8))

    payment_type = getattr(order, 'get_payment_type_display', None)
    payment_status = getattr(order, 'get_payment_status_display', None)
    payment_type_text = payment_type() if callable(payment_type) else order.payment_type
    payment_status_text = payment_status() if callable(payment_status) else order.payment_status

    info_data = [
        ['Order ID', f'#{order.id}'],
        ['Invoice No.', _invoice_number(order)],
        ['Customer', order.full_name],
        ['Phone', order.phone],
        ['Address', order.address],
        ['Payment Type', payment_type_text],
        ['Payment Status', payment_status_text],
        ['Created At', timezone.localtime(order.created_at).strftime('%Y-%m-%d %H:%M')],
    ]
    info_table = Table(info_data, colWidths=[110, 380])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.whitesmoke),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.lightgrey),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 12))

    items = order.items.select_related('product').all()
    items_data = [['Product', 'Quantity', 'Price']]
    for item in items:
        items_data.append([
            item.product.name,
            str(item.quantity),
            f"{item.price}",
        ])

    items_table = Table(items_data, colWidths=[280, 80, 130])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.black),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 12))

    summary_data = [
        ['Total', f"{order.total_price}"],
        ['Payment Type', payment_type_text],
        ['Date', timezone.localtime(order.created_at).strftime('%Y-%m-%d')],
    ]
    summary_table = Table(summary_data, colWidths=[140, 320])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 10))

    qr_value = f"ORDER:{order.id}|INVOICE:{_invoice_number(order)}|TOTAL:{order.total_price}"
    qr_code = QrCodeWidget(qr_value)
    bounds = qr_code.getBounds()
    qr_width = bounds[2] - bounds[0]
    qr_height = bounds[3] - bounds[1]
    qr_size = 28 * mm
    qr_drawing = Drawing(qr_size, qr_size, transform=[qr_size / qr_width, 0, 0, qr_size / qr_height, 0, 0])
    qr_drawing.add(qr_code)
    story.append(Paragraph('Scan for order details', styles['Normal']))
    story.append(qr_drawing)

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename=\"order_{order.id}.pdf\"'
    response.write(pdf)
    return response


def export_invoice_xml(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if not _order_access_allowed(request.user, order):
        return HttpResponseForbidden('Access denied')

    root = ET.Element('Invoice')
    ET.SubElement(root, 'Seller').text = 'DEMO MOTOR SHOP'
    ET.SubElement(root, 'InvoiceNumber').text = _invoice_number(order)

    buyer = ET.SubElement(root, 'Buyer')
    ET.SubElement(buyer, 'Name').text = order.full_name
    ET.SubElement(buyer, 'Phone').text = order.phone
    ET.SubElement(buyer, 'Address').text = order.address

    items_el = ET.SubElement(root, 'Items')
    for item in order.items.select_related('product').all():
        item_el = ET.SubElement(items_el, 'Item')
        ET.SubElement(item_el, 'Name').text = item.product.name
        ET.SubElement(item_el, 'Quantity').text = str(item.quantity)
        ET.SubElement(item_el, 'Price').text = str(item.price)

    ET.SubElement(root, 'Total').text = str(order.total_price)
    payment_type = getattr(order, 'get_payment_type_display', None)
    payment_type_text = payment_type() if callable(payment_type) else order.payment_type
    ET.SubElement(root, 'PaymentType').text = payment_type_text
    ET.SubElement(root, 'CreatedAt').text = timezone.localtime(order.created_at).isoformat()

    xml_bytes = ET.tostring(root, encoding='utf-8', xml_declaration=True)
    response = HttpResponse(xml_bytes, content_type='application/xml')
    response['Content-Disposition'] = f'attachment; filename=\"invoice_{order.id}.xml\"'
    return response

@login_required
def order_return_request(request, pk):
    # This view now redirects to the form
    return redirect('shops:order_return_request_form', pk=pk)

@login_required
def order_return_request_form(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    if not order.can_return:
        messages.error(request, 'Không thể yêu cầu hoàn trả cho đơn hàng này.')
        return redirect('shops:order_detail', pk=pk)
    
    if request.method == 'POST':
        reason = request.POST.get('reason')
        image = request.FILES.get('image')
        if reason:
            with transaction.atomic():
                ReturnRequest.objects.create(
                    order=order,
                    reason=reason,
                    image=image
                )
                order.status = 'return_requested'
                order.save()
            messages.success(request, f'Yêu cầu hoàn trả cho đơn hàng #{order.id} đã được gửi thành công.')
            return redirect('shops:order_detail', pk=pk)
        else:
            messages.error(request, 'Vui lòng nhập lý do hoàn trả.')
            
    return render(request, 'shops/return_request_form.html', {'order': order})

@staff_member_required
def admin_return_requests_list(request):
    requests = ReturnRequest.objects.select_related('order').order_by('-created_at')
    return render(request, 'shops/admin_return_requests.html', {'requests': requests})

@staff_member_required
def admin_confirm_payment(request, pk):
    if request.method == 'POST':
        order = get_object_or_404(Order, pk=pk)
        order.payment_status = 'paid'
        order.save()
        messages.success(request, f'Đã xác nhận thanh toán cho đơn hàng #{order.id}.')
    return redirect('shops:order_detail', pk=pk)

@staff_member_required
def admin_update_order_status(request, pk):
    if request.method == 'POST':
        order = get_object_or_404(Order, pk=pk)
        new_status = request.POST.get('status')
        if new_status in dict(Order.STATUS_CHOICES):
            order.status = new_status
            order.save()
            messages.success(request, f'Trạng thái đơn hàng #{order.id} đã được cập nhật thành {order.get_status_display()}.')
        else:
            messages.error(request, 'Trạng thái không hợp lệ.')
    return redirect('shops:order_detail', pk=pk)
