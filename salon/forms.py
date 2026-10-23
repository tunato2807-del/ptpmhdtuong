from datetime import timedelta
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.utils import timezone
from .models import User, Branch, Employee, Service, Review

class LoginForm(AuthenticationForm):
    username = forms.CharField(label='Tên đăng nhập', widget=forms.TextInput(attrs={'autofocus': True, 'autocomplete': 'username'}))
    password = forms.CharField(label='Mật khẩu', strip=False, widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}))

class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['full_name', 'username', 'phone', 'email', 'password1', 'password2']
        labels = {'username': 'Tên đăng nhập', 'email': 'Email'}
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['full_name'].required = True
        self.fields['phone'].required = True
        self.fields['email'].required = True
        self.fields['username'].help_text = 'Chữ cái, chữ số và @/./+/-/_.'

class BookingForm(forms.Form):
    branch = forms.ModelChoiceField(label='Chi nhánh', queryset=Branch.objects.filter(active=True), empty_label='Chọn chi nhánh')
    services = forms.ModelMultipleChoiceField(label='Dịch vụ', queryset=Service.objects.filter(active=True), widget=forms.CheckboxSelectMultiple)
    employee = forms.ModelChoiceField(label='Stylist', queryset=Employee.objects.filter(active=True, branch__active=True), empty_label='Chọn stylist')
    date = forms.DateField(label='Ngày hẹn', widget=forms.DateInput(attrs={'type': 'date'}))
    time = forms.TimeField(label='Giờ hẹn', input_formats=['%H:%M'], widget=forms.HiddenInput)
    note = forms.CharField(label='Lời nhắn cho stylist', required=False, max_length=500, widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Ví dụ: tư vấn kiểu tóc phù hợp, giữ phần mái dài…'}))
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user and user.is_operator:
            customers = User.objects.filter(role=User.Role.CUSTOMER, is_active=True)
            if user.role == User.Role.RECEPTIONIST:
                customers = customers.filter(appointments__branch_id=user.branch_id).distinct()
                self.fields['branch'].queryset = Branch.objects.filter(pk=user.branch_id, active=True)
                self.fields['employee'].queryset = Employee.objects.filter(branch_id=user.branch_id, active=True)
            self.fields['customer'] = forms.ModelChoiceField(label='Đặt cho khách hàng', queryset=customers.order_by('full_name'), empty_label='Chọn khách hàng')
            self.fields['customer'].label_from_instance = lambda obj: f'{obj.full_name} · {obj.phone}'
        today = timezone.localdate()
        self.fields['date'].widget.attrs.update({'min': today.isoformat(), 'max': (today+timedelta(days=30)).isoformat()})
    def clean(self):
        data = super().clean()
        if data.get('employee') and data.get('branch') and data['employee'].branch_id != data['branch'].pk:
            self.add_error('employee', 'Stylist không thuộc chi nhánh đã chọn.')
        return data

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {'rating': forms.Select(choices=[(i, f'{i} sao') for i in range(5,0,-1)]),
                   'comment': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Chia sẻ trải nghiệm của bạn…'})}
