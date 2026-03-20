def cart_count(request):
    """
    Temporary mock context processor for cart count.
    Replace with actual logic later.
    """
    return {'cart_count': 0}

def notification_context(request):
    """
    Provide unread notification count for navbar.
    """
    if request.user.is_authenticated:
        from .models import Notification
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
        return {'unread_notification_count': unread_count}
    return {'unread_notification_count': 0}


def wishlist_context(request):
    if request.user.is_authenticated:
        from .models import Wishlist
        qs = Wishlist.objects.filter(user=request.user)
        return {
            'wishlist_product_ids': list(qs.values_list('product_id', flat=True)),
            'wishlist_count': qs.count(),
        }
    return {
        'wishlist_product_ids': [],
        'wishlist_count': 0,
    }
