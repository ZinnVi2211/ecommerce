from django.core.management.base import BaseCommand
from django.utils.text import slugify

from shops.models import Category, Product


class Command(BaseCommand):
    help = "Seed demo motorcycle products"

    def handle(self, *args, **options):
        category, _ = Category.objects.get_or_create(
            slug='motorcycles',
            defaults={
                'name': 'Motorcycles',
                'description': 'Danh mục xe máy/mô tô',
                'is_active': True
            }
        )

        # Clear old demo products in this category
        Product.objects.filter(category=category).delete()

        motorcycles = [
            {
                'name': 'Honda Winner X',
                'price': 46500000,
                'engine': '150cc',
                'fuel_consumption': '1.99L/100km',
                'colors': ['Đỏ', 'Đen', 'Xanh'],
                'versions': ['Standard', 'ABS', 'Premium'],
                'stock': 12,
                'description': 'Thiết kế thể thao, động cơ mạnh mẽ và tiết kiệm nhiên liệu.'
            },
            {
                'name': 'Yamaha Exciter 155 VVA',
                'price': 54500000,
                'engine': '155cc',
                'fuel_consumption': '2.2L/100km',
                'colors': ['Xanh GP', 'Đen', 'Trắng'],
                'versions': ['Standard', 'ABS', 'GP Edition'],
                'stock': 15,
                'description': 'Dáng thể thao, VVA bứt tốc mạnh mẽ, phù hợp đi phố.'
            },
            {
                'name': 'Suzuki Raider R150',
                'price': 48900000,
                'engine': '150cc',
                'fuel_consumption': '2.0L/100km',
                'colors': ['Đỏ', 'Đen', 'Xám'],
                'versions': ['Standard', 'ABS'],
                'stock': 10,
                'description': 'Underbone thể thao với động cơ DOHC mạnh mẽ.'
            },
            {
                'name': 'Honda Air Blade 160',
                'price': 57900000,
                'engine': '160cc',
                'fuel_consumption': '2.3L/100km',
                'colors': ['Xám', 'Đen', 'Đỏ'],
                'versions': ['Standard', 'ABS', 'Special'],
                'stock': 18,
                'description': 'Xe tay ga cao cấp, vận hành êm ái và bền bỉ.'
            },
            {
                'name': 'Yamaha NVX 155',
                'price': 54900000,
                'engine': '155cc',
                'fuel_consumption': '2.4L/100km',
                'colors': ['Xanh', 'Đen', 'Trắng'],
                'versions': ['Standard', 'ABS'],
                'stock': 14,
                'description': 'Scooter thể thao, tư thế lái thoải mái, tiện ích hiện đại.'
            },
            {
                'name': 'Honda SH 160i',
                'price': 92900000,
                'engine': '160cc',
                'fuel_consumption': '2.2L/100km',
                'colors': ['Trắng', 'Đen', 'Xám'],
                'versions': ['Standard', 'ABS'],
                'stock': 8,
                'description': 'Biểu tượng tay ga cao cấp, sang trọng và đẳng cấp.'
            },
            {
                'name': 'Vespa Sprint 150',
                'price': 79900000,
                'engine': '150cc',
                'fuel_consumption': '2.6L/100km',
                'colors': ['Vàng', 'Đỏ', 'Xanh'],
                'versions': ['Standard', 'Sport'],
                'stock': 9,
                'description': 'Thiết kế Ý cổ điển, phong cách trẻ trung, sang trọng.'
            },
            {
                'name': 'Kawasaki Ninja 400',
                'price': 169000000,
                'engine': '399cc',
                'fuel_consumption': '4.2L/100km',
                'colors': ['Xanh KRT', 'Đen', 'Trắng'],
                'versions': ['Standard', 'ABS'],
                'stock': 7,
                'description': 'Sportbike dễ lái, cân bằng giữa hiệu năng và kiểm soát.'
            },
            {
                'name': 'Yamaha R15 V4',
                'price': 78900000,
                'engine': '155cc',
                'fuel_consumption': '2.1L/100km',
                'colors': ['Xanh GP', 'Đen', 'Trắng'],
                'versions': ['Standard', 'ABS'],
                'stock': 11,
                'description': 'Sportbike phổ thông với thiết kế DNA R-Series.'
            },
            {
                'name': 'Honda CBR150R',
                'price': 72900000,
                'engine': '150cc',
                'fuel_consumption': '2.2L/100km',
                'colors': ['Đỏ', 'Đen', 'Trắng'],
                'versions': ['Standard', 'ABS'],
                'stock': 13,
                'description': 'Phong cách thể thao, vận hành mượt và ổn định.'
            },
            {
                'name': 'Suzuki GSX-R150',
                'price': 74900000,
                'engine': '150cc',
                'fuel_consumption': '2.0L/100km',
                'colors': ['Xanh', 'Đen', 'Đỏ'],
                'versions': ['Standard', 'ABS'],
                'stock': 9,
                'description': 'Thiết kế khí động học, hiệu năng tối ưu cho đường phố.'
            },
            {
                'name': 'Honda Rebel 500',
                'price': 181000000,
                'engine': '471cc',
                'fuel_consumption': '3.2L/100km',
                'colors': ['Đen', 'Xám'],
                'versions': ['Standard'],
                'stock': 6,
                'description': 'Cruiser cá tính, yên thấp dễ lái, phong cách mạnh mẽ.'
            },
            {
                'name': 'Yamaha MT-03',
                'price': 139000000,
                'engine': '321cc',
                'fuel_consumption': '3.8L/100km',
                'colors': ['Xanh', 'Đen'],
                'versions': ['Standard', 'ABS'],
                'stock': 7,
                'description': 'Naked bike gọn gàng, linh hoạt và mạnh mẽ.'
            },
            {
                'name': 'KTM Duke 390',
                'price': 191000000,
                'engine': '373cc',
                'fuel_consumption': '3.4L/100km',
                'colors': ['Cam', 'Đen'],
                'versions': ['Standard', 'ABS'],
                'stock': 5,
                'description': 'Cấu hình mạnh, trọng lượng nhẹ, phù hợp đô thị.'
            },
            {
                'name': 'BMW G 310 R',
                'price': 189000000,
                'engine': '313cc',
                'fuel_consumption': '3.3L/100km',
                'colors': ['Trắng', 'Đen', 'Đỏ'],
                'versions': ['Standard', 'ABS'],
                'stock': 6,
                'description': 'Naked bike phong cách Đức, gọn nhẹ và bền bỉ.'
            },
        ]

        created_count = 0
        for item in motorcycles:
            base_slug = slugify(item['name'])
            slug = base_slug
            idx = 1
            while Product.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{idx}"
                idx += 1

            Product.objects.create(
                category=category,
                name=item['name'],
                slug=slug,
                price=item['price'],
                stock=item['stock'],
                description=item['description'],
                engine=item['engine'],
                fuel_consumption=item['fuel_consumption'],
                color_options=item['colors'],
                version_options=item['versions'],
                available=True
            )
            created_count += 1

        self.stdout.write(self.style.SUCCESS(f"Seeded {created_count} motorcycles successfully."))
