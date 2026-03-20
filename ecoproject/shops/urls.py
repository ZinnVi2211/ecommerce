from django.urls import path
from . import views
from django.views.generic import RedirectView

app_name = 'shops'

urlpatterns = [
    path('', views.index, name='index'),
    path('dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    path('dashboard/api/', views.dashboard_api, name='admin_dashboard_api'),
    path('products/', views.product_list, name='product_list'),
    path('products/create/', views.product_create, name='product_create'),
    path('products/<int:id>/update/', views.product_update, name='product_update'),
    path('products/<int:id>/delete/', views.product_delete, name='product_delete'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<int:id>/update/', views.category_update, name='category_update'),
    path('categories/<int:id>/delete/', views.category_delete, name='category_delete'),
    path('products/<slug:category_slug>/', views.product_list, name='product_list_by_category'),
    path('wishlist/', views.wishlist_view, name='wishlist_view'),
    path('wishlist/toggle/<int:product_id>/', views.toggle_wishlist, name='wishlist_toggle'),
    path('notifications/', views.notification_list_view, name='notification_list'),
    path('notifications/api/', views.notification_dropdown_api, name='notification_api'),
    path('notifications/read/<int:id>/', views.mark_as_read, name='notification_read'),
    path('notifications/read-all/', views.mark_all_as_read, name='notification_read_all'),

    # Checkout flows
    path('cart/', views.cart_view, name='cart_view'),
    path('add-to-cart/<int:id>/', views.add_to_cart, name='add_to_cart'),
    path('remove/<int:id>/', views.remove_from_cart, name='remove_from_cart'),
    path('update-cart-item/<int:id>/', views.update_cart_item, name='update_cart_item'),
    path('checkout/', views.checkout_view, name='checkout_view'),
    path('place-order/', views.place_order, name='place_order'),
    path('success/', views.order_success, name='order_success'),
    path('order-status/', views.order_status, name='order_status'),
    path('order-history/', views.order_history, name='order_history'),
    path('order/<int:pk>/', views.order_detail, name='order_detail'),
    path('order/<int:pk>/cancel/', views.order_cancel, name='order_cancel'),
    path('order/<int:pk>/return/', views.order_return_request, name='order_return_request'),
    path('order/<int:pk>/update-status/', views.admin_update_order_status, name='admin_update_order_status'),
    path('order/<int:pk>/return-form/', views.order_return_request_form, name='order_return_request_form'),
    path('admin/returns/', views.admin_return_requests_list, name='admin_return_requests_list'),
    path('order/<int:pk>/confirm-payment/', views.admin_confirm_payment, name='admin_confirm_payment'),
    path('product/<slug:slug>/', views.product_detail_view, name='product_detail'),
    # Redirect old motorcycle links to new product detail
    path('motorcycles/<slug:slug>/', RedirectView.as_view(pattern_name='shops:product_detail', permanent=True)),
]
