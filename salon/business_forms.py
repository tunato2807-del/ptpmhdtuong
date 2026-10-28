from django import forms
from django.core.exceptions import ValidationError
from .models import Branch, User, Employee, Service, Product, Voucher
from .forms import BranchForm, EmployeeForm, AccountForm
from .views import branches_for

DATE_WIDGET = forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M")


class WalkInForm(forms.Form):
    branch = forms.ModelChoiceField(label="Chi nhánh tiếp nhận", queryset=Branch.objects.none())
    customer = forms.ModelChoiceField(
        label="Khách cũ tại chi nhánh (nếu có)", queryset=User.objects.none(), required=False
    )
    name = forms.CharField(
        label="Họ tên khách mới / khách theo điện thoại", max_length=100, required=False
    )
    phone = forms.CharField(label="Điện thoại", max_length=10, required=False)
    email = forms.EmailField(label="Email nhận lịch hẹn", required=False)
    employee = forms.ModelChoiceField(label="Stylist", queryset=Employee.objects.none())
    services = forms.ModelMultipleChoiceField(
        label="Dịch vụ",
        queryset=Service.objects.filter(active=True),
        widget=forms.CheckboxSelectMultiple,
    )
    start = forms.DateTimeField(label="Giờ dự kiến (bước 15 phút)", widget=DATE_WIDGET)

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        scope = branches_for(user).filter(active=True)
        self.fields["branch"].queryset = scope
        self.fields["employee"].queryset = Employee.objects.filter(branch__in=scope, active=True)
        customers = User.objects.filter(role="customer", is_active=True)
        if not user.is_manager:
            customers = customers.filter(appointments__branch__in=scope).distinct()
        self.fields["customer"].queryset = customers

    def clean(self):
        d = super().clean()
        if d.get("branch") and d.get("employee") and d["employee"].branch_id != d["branch"].pk:
            self.add_error("employee", "Stylist không thuộc chi nhánh đã chọn.")
        if not d.get("customer") and (not d.get("name") or not d.get("phone")):
            raise ValidationError("Chọn khách cũ hoặc nhập đủ họ tên và điện thoại.")
        return d


class ServicesForm(forms.Form):
    services = forms.ModelMultipleChoiceField(
        label="Dịch vụ sau điều chỉnh",
        queryset=Service.objects.filter(active=True),
        widget=forms.CheckboxSelectMultiple,
    )
    reason = forms.CharField(
        label="Lý do điều chỉnh", max_length=250, widget=forms.Textarea(attrs={"rows": 3})
    )
    confirm = forms.BooleanField(
        label="Khách đã đồng ý các dịch vụ, giá và thời lượng sau điều chỉnh."
    )


class ExtendForm(forms.Form):
    minutes = forms.TypedChoiceField(
        label="Thời gian thêm", coerce=int, choices=[(n, f"{n} phút") for n in (15, 30, 45, 60)]
    )
    reason = forms.CharField(label="Lý do phục vụ kéo dài", max_length=250)


class InterruptionForm(forms.Form):
    branch = forms.ModelChoiceField(label="Chi nhánh", queryset=Branch.objects.none())
    employee = forms.ModelChoiceField(
        label="Stylist nghỉ (để trống nếu cả chi nhánh nghỉ)",
        required=False,
        queryset=Employee.objects.none(),
    )
    start = forms.DateTimeField(label="Bắt đầu nghỉ", widget=DATE_WIDGET)
    end = forms.DateTimeField(label="Kết thúc nghỉ", widget=DATE_WIDGET)
    reason = forms.CharField(
        label="Lý do", max_length=250, widget=forms.Textarea(attrs={"rows": 3})
    )
    confirm = forms.BooleanField(
        label="Tôi sẽ liên hệ và xử lý tất cả lịch bị ảnh hưởng; hệ thống giữ lịch để điều phối."
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["branch"].queryset = branches_for(user)
        self.fields["employee"].queryset = Employee.objects.filter(
            branch__in=branches_for(user), active=True
        )

    def clean(self):
        d = super().clean()
        if d.get("start") and d.get("end") and d["end"] <= d["start"]:
            self.add_error("end", "Kết thúc phải sau bắt đầu.")
        if d.get("branch") and d.get("employee") and d["employee"].branch_id != d["branch"].pk:
            self.add_error("employee", "Stylist khác chi nhánh.")
        return d


class RefundForm(forms.Form):
    reason = forms.CharField(
        label="Lý do hoàn toàn bộ tiền", max_length=250, widget=forms.Textarea(attrs={"rows": 3})
    )
    confirm = forms.BooleanField(
        label="Tôi xác nhận đã hoàn tiền cho khách và đối chiếu chứng từ. Đây là ghi nhận nội bộ, không tự chuyển tiền ngân hàng."
    )


class ClosingForm(forms.Form):
    branch = forms.ModelChoiceField(label="Chi nhánh", queryset=Branch.objects.none())
    day = forms.DateField(label="Ngày chốt", widget=forms.DateInput(attrs={"type": "date"}))
    counted = forms.IntegerField(label="Tiền mặt thực đếm từ giao dịch trong ngày (đ)", min_value=0)
    reason = forms.CharField(
        label="Giải trình chênh lệch / ghi chú", max_length=250, required=False
    )
    confirm = forms.BooleanField(
        label="Đã đối soát các giao dịch. Ngày chốt không nhận thêm giao dịch thu/hoàn tiền."
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["branch"].queryset = branches_for(user)


class StockForm(forms.Form):
    branch = forms.ModelChoiceField(label="Chi nhánh xuất / nhận", queryset=Branch.objects.none())
    product = forms.ModelChoiceField(
        label="Sản phẩm / vật tư", queryset=Product.objects.filter(active=True)
    )
    kind = forms.ChoiceField(
        label="Loại giao dịch",
        choices=[
            ("receipt", "Nhập kho"),
            ("consume", "Xuất sử dụng"),
            ("adjust", "Điều chỉnh tăng/giảm sau kiểm kê"),
            ("transfer", "Chuyển sang chi nhánh khác"),
        ],
    )
    amount = forms.IntegerField(
        label="Số lượng (kiểm kê dùng chênh lệch có dấu)", min_value=-1000000, max_value=1000000
    )
    target = forms.ModelChoiceField(
        label="Chi nhánh nhận nếu chuyển kho",
        required=False,
        queryset=Branch.objects.filter(active=True),
    )
    reason = forms.CharField(label="Lý do / số chứng từ", max_length=250)

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["branch"].queryset = branches_for(user)
        if not user.is_manager:
            self.fields["kind"].choices = self.fields["kind"].choices[:-1]
            self.fields.pop("target")

    def clean(self):
        d = super().clean()
        if d.get("kind") == "transfer" and not d.get("target"):
            self.add_error("target", "Chọn chi nhánh nhận.")
        if d.get("amount") == 0:
            self.add_error("amount", "Số lượng không được bằng 0.")
        return d


class PolicyForm(BranchForm):
    class Meta(BranchForm.Meta):
        fields = BranchForm.Meta.fields + ["booking_days", "cancel_hours", "late_minutes"]


class StylistForm(EmployeeForm):
    class Meta(EmployeeForm.Meta):
        fields = EmployeeForm.Meta.fields + ["account", "commission_percent"]

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["branch"].queryset = branches_for(user)
        self.fields["account"].queryset = User.objects.filter(
            role="stylist", branch__in=branches_for(user), is_active=True
        )

    def clean(self):
        d = super().clean()
        if d.get("account") and d.get("branch") and d["account"].branch_id != d["branch"].pk:
            self.add_error("account", "Tài khoản stylist phải thuộc đúng chi nhánh.")
        return d


class BranchAccountForm(AccountForm):
    def __init__(self, *args, actor, **kwargs):
        super().__init__(*args, actor=actor, **kwargs)
        self.fields["branch"].queryset = branches_for(actor)
        if not actor.is_manager:
            self.fields["role"].choices = [("receptionist", "Lễ tân"), ("stylist", "Stylist")]

    def clean(self):
        d = super().clean()
        if self.instance.pk and hasattr(self.instance, "stylist_profile"):
            e = self.instance.stylist_profile
            if d.get("role") != "stylist" or not d.get("branch") or d["branch"].pk != e.branch_id:
                raise ValidationError(
                    "Tài khoản đã gắn stylist phải giữ vai trò và chi nhánh tương ứng."
                )
        return d


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["sku", "name", "unit", "reorder_level", "active"]


class VoucherForm(forms.ModelForm):
    class Meta:
        model = Voucher
        fields = [
            "code",
            "branch",
            "amount",
            "min_total",
            "starts_at",
            "ends_at",
            "max_uses",
            "active",
        ]
        widgets = {"starts_at": DATE_WIDGET, "ends_at": DATE_WIDGET}

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["branch"].queryset = branches_for(user)
        if not user.is_manager:
            self.fields["branch"].required = True

    def clean_code(self):
        code = self.cleaned_data["code"].strip().upper()
        if Voucher.objects.filter(code__iexact=code).exclude(pk=self.instance.pk).exists():
            raise ValidationError("Mã voucher đã tồn tại.")
        return code

    def clean(self):
        d = super().clean()
        if d.get("starts_at") and d.get("ends_at") and d["ends_at"] <= d["starts_at"]:
            self.add_error("ends_at", "Ngày kết thúc phải sau bắt đầu.")
        if self.instance.pk and self.instance.uses.exists():
            for field in ("amount", "min_total", "branch", "code"):
                value = d.get(field)
                old = getattr(self.instance, field)
                # ModelForm has not copied cleaned_data to instance yet.
                if value != old:
                    self.add_error(
                        field,
                        "Voucher đã có giao dịch: giữ nguyên giá trị, chi nhánh và mã; có thể ngừng hoặc chỉnh thời hạn/lượt.",
                    )
        return d


class CustomerContactForm(forms.ModelForm):
    verified = forms.BooleanField(
        label="Đã xác minh khách hàng và được khách đồng ý cập nhật thông tin liên hệ."
    )

    class Meta:
        model = User
        fields = ["full_name", "phone", "email"]

    def __init__(self, *args, actor, **kwargs):
        super().__init__(*args, **kwargs)
        # An email address is also a password recovery credential. Branch staff
        # may enroll only their own blank-mailbox, unactivated walk-in profile.
        local_guest = (
            not self.instance.has_usable_password()
            and not self.instance.email
            and not self.instance.appointments.exclude(branch_id=actor.branch_id).exists()
        )
        if not actor.is_manager and not local_guest:
            self.fields["email"].disabled = True
            self.fields[
                "email"
            ].help_text = "Email đăng nhập do chủ tài khoản hoặc quản trị chuỗi cập nhật. Chi nhánh không thể đổi email khôi phục mật khẩu."

    def clean_phone(self):
        value = self.cleaned_data["phone"]
        if (
            value
            and User.objects.filter(role="customer", phone=value)
            .exclude(pk=self.instance.pk)
            .exists()
        ):
            raise ValidationError(
                "Điện thoại đang thuộc hồ sơ khác. Không tự gộp hồ sơ; liên hệ quản trị xác minh."
            )
        return value
