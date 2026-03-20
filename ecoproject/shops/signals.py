from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.urls import reverse
from .models import Order, Notification


@receiver(pre_save, sender=Order)
def capture_previous_order_state(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_status = None
        instance._previous_payment_status = None
        return
    previous = Order.objects.filter(pk=instance.pk).values('status', 'payment_status').first()
    instance._previous_status = previous['status'] if previous else None
    instance._previous_payment_status = previous['payment_status'] if previous else None


@receiver(post_save, sender=Order)
def create_order_notifications(sender, instance, created, **kwargs):
    if not instance.user:
        return

    order_link = reverse('shops:order_history')
    if created:
        Notification.objects.create(
            user=instance.user,
            title='Đơn hàng mới',
            message=f'Đơn #{instance.id} đã được tạo thành công.',
            type='order',
            link=order_link
        )

    if instance.payment_status == 'paid' and instance._previous_payment_status != 'paid':
        Notification.objects.create(
            user=instance.user,
            title='Thanh toán thành công',
            message=f'Đơn #{instance.id} đã được thanh toán đầy đủ.',
            type='payment',
            link=order_link
        )

    if instance._previous_status and instance.status != instance._previous_status:
        Notification.objects.create(
            user=instance.user,
            title='Cập nhật trạng thái đơn',
            message=f'Đơn #{instance.id} đã chuyển sang trạng thái "{instance.get_status_display()}".',
            type='order',
            link=order_link
        )
