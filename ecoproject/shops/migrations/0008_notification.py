from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('shops', '0007_wishlist'),
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('message', models.TextField()),
                ('type', models.CharField(choices=[('order', 'Order'), ('payment', 'Payment'), ('promotion', 'Promotion'), ('wishlist', 'Wishlist')], default='order', max_length=20)),
                ('is_read', models.BooleanField(default=False)),
                ('link', models.URLField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'notification',
                'verbose_name_plural': 'notifications',
                'ordering': ['-created_at'],
                'indexes': [models.Index(fields=['user', 'is_read'], name='shops_notif_user_is_read_idx')],
            },
        ),
    ]
