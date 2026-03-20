from django import forms
from .models import Product, Category

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'slug', 'image', 'image_url', 'description', 'is_active']
        labels = {
            'name': 'Tên danh mục',
            'slug': 'Đường dẫn (Slug)',
            'image': 'Hình ảnh',
            'image_url': 'Link hình ảnh',
            'description': 'Mô tả',
            'is_active': 'Kích hoạt / Hiển thị'
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nhập tên danh mục...', 'oninput': 'generateSlug()'}),
            'slug': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'tu-dong-tao-tu-ten', 'id': 'id_slug'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'image_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'Dán link hình ảnh (https://...)'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Mô tả danh mục...'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }

    def clean(self):
        cleaned_data = super().clean()
        image = cleaned_data.get('image')
        image_url = cleaned_data.get('image_url')
        if not image and not image_url:
            self.add_error('image', 'Vui lòng chọn ảnh hoặc dán link ảnh.')
            self.add_error('image_url', 'Vui lòng chọn ảnh hoặc dán link ảnh.')
        return cleaned_data

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['category', 'name', 'slug', 'image', 'image_url', 'description', 'price', 'stock', 'available']
        labels = {
            'category': 'Danh mục',
            'name': 'Tên sản phẩm',
            'slug': 'Đường dẫn (Slug)',
            'image': 'Hình ảnh',
            'image_url': 'Link hình ảnh',
            'description': 'Mô tả',
            'price': 'Giá bán (VNĐ)',
            'stock': 'Số lượng kho',
            'available': 'Đang bán',
        }
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nhập tên xe...', 'oninput': 'generateSlug()'}),
            'slug': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'tu-dong-tao-tu-ten', 'id': 'id_slug'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'image_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'Dán link hình ảnh (https://...)'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Mô tả chi tiết sản phẩm...'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ví dụ: 250000000'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Số lượng hiện có'}),
            'available': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }

    def clean(self):
        cleaned_data = super().clean()
        image = cleaned_data.get('image')
        image_url = cleaned_data.get('image_url')
        if not image and not image_url:
            self.add_error('image', 'Vui lòng chọn ảnh hoặc dán link ảnh.')
            self.add_error('image_url', 'Vui lòng chọn ảnh hoặc dán link ảnh.')
        return cleaned_data


class CheckoutForm(forms.Form):
    full_name = forms.CharField(max_length=255, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Họ và tên'}))
    phone = forms.CharField(max_length=20, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Số điện thoại'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}))
    address = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Địa chỉ giao hàng'}))
    city = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Thành phố'}))
    payment_type = forms.ChoiceField(
        choices=[
            ('deposit', 'Đặt cọc 10%'),
            ('full', 'Thanh toán toàn bộ'),
            ('showroom', 'Thanh toán tại showroom'),
            ('bank_transfer', 'Chuyển khoản ngân hàng'),
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if not phone.isdigit():
            raise forms.ValidationError('Số điện thoại phải là số.')
        return phone


class OrderStatusForm(forms.Form):
    order_id = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Mã đơn (VD: 1024)'}),
        label='Mã đơn'
    )
    phone_or_email = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Số điện thoại hoặc Email'}),
        label='Số điện thoại / Email'
    )

    def clean_phone_or_email(self):
        value = self.cleaned_data.get('phone_or_email', '').strip()
        if not value:
            raise forms.ValidationError('Vui lòng nhập số điện thoại hoặc email.')
        return value
