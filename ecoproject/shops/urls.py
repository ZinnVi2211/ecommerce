from django.urls import path
from . import views

app_name = 'shops'

urlpatterns = [
    path('', views.index, name='index'),
    path('products/', views.product_list, name='product_list'),
    path('products/create/', views.product_create, name='product_create'),
    path('products/<int:id>/update/', views.product_update, name='product_update'),
    path('products/<int:id>/delete/', views.product_delete, name='product_delete'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<int:id>/update/', views.category_update, name='category_update'),
    path('categories/<int:id>/delete/', views.category_delete, name='category_delete'),
    path('products/<slug:category_slug>/', views.product_list, name='product_list_by_category'),
    path('motorcycles/', views.MotorcycleListView.as_view(), name='motorcycle_list'),
    path('motorcycles/<slug:slug>/', views.MotorcycleDetailView.as_view(), name='motorcycle_detail'),

    # Checkout flows
    path('cart/', views.cart_view, name='cart_view'),
    path('add-to-cart/<int:id>/', views.add_to_cart, name='add_to_cart'),
    path('remove/<int:id>/', views.remove_from_cart, name='remove_from_cart'),
    path('update-cart-item/<int:id>/', views.update_cart_item, name='update_cart_item'),
    path('apply-voucher/', views.apply_voucher, name='apply_voucher'),
    path('checkout/', views.checkout_view, name='checkout_view'),
    path('place-order/', views.place_order, name='place_order'),
    path('success/', views.order_success, name='order_success'),
    path('order-status/', views.order_status, name='order_status'),
    path('product/<slug:slug>/', views.product_detail_view, name='product_detail'),
]
