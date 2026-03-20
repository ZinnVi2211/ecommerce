from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView
from django.http import Http404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.urls import reverse

from .models import Category, Product, Cart, CartItem, Order, OrderItem, Voucher
from .forms import ProductForm, CategoryForm, CheckoutForm, OrderStatusForm

def index(request):
    return render(request, 'shops/index.html')

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
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f'Sản phẩm "{product.name}" đã được cập nhật!')
            return redirect('shops:product_list')
    else:
        form = ProductForm(instance=product)
    return render(request, 'shops/product_form.html', {'form': form, 'title': 'Cập nhật sản phẩm', 'product': product})

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

    voucher_code = request.session.get('voucher_code')
    voucher = None
    discount_value = 0
    if voucher_code:
        voucher = Voucher.objects.filter(code__iexact=voucher_code).first()
        if voucher and voucher.is_valid():
            discount_value = (cart.total_price() * voucher.discount_percent) / 100
        else:
            voucher = None
            request.session.pop('voucher_code', None)

    subtotal = cart.total_price()
    total = max(0, subtotal - discount_value)

    return render(request, 'shops/cart.html', {
        'cart': cart,
        'items': items,
        'subtotal': subtotal,
        'discount': discount_value,
        'total': total,
        'voucher': voucher,
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


def apply_voucher(request):
    if request.method != 'POST':
        return redirect('shops:cart_view')

    cart = _get_or_create_cart(request)
    subtotal = cart.total_price()
    code = request.POST.get('code', '').strip()
    voucher = Voucher.objects.filter(code__iexact=code).first()

    if not voucher or not voucher.is_valid():
        messages.error(request, 'Mã voucher không hợp lệ hoặc đã hết hạn.')
        request.session.pop('voucher_code', None)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': 'Voucher không hợp lệ.',
                'subtotal': float(subtotal),
                'discount': 0,
                'total': float(subtotal),
            })
        return redirect('shops:cart_view')

    request.session['voucher_code'] = voucher.code
    request.session.modified = True
    messages.success(request, f'Áp dụng voucher {voucher.code} thành công ({voucher.discount_percent}% giảm).')

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        discount_value = (subtotal * voucher.discount_percent) / 100
        total = max(0, subtotal - discount_value)
        return JsonResponse({
            'success': True,
            'code': voucher.code,
            'discount_percent': voucher.discount_percent,
            'subtotal': float(subtotal),
            'discount': float(discount_value),
            'total': float(total),
        })

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

    voucher = None
    discount_value = 0
    voucher_code = request.session.get('voucher_code')
    if voucher_code:
        voucher = Voucher.objects.filter(code__iexact=voucher_code).first()
        if voucher and voucher.is_valid():
            discount_value = (cart.total_price() * voucher.discount_percent) / 100
        else:
            voucher = None
            request.session.pop('voucher_code', None)

    subtotal = cart.total_price()
    total = max(0, subtotal - discount_value)

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
        'discount': discount_value,
        'total': total,
        'voucher': voucher,
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
