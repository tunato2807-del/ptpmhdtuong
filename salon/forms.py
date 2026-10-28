from datetime import timedelta
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.utils import timezone
from django.db.models import Q
from .models import (
    User,
    Branch,
    Employee,
    Service,
    Review,
    Chair,
    Shift,
    Appointment,
    ACTIVE_STATUSES,
)


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Tên đăng nhập",
        widget=forms.TextInput(attrs={"autofocus": True, "autocomplete": "username"}),
    )
    password = forms.CharField(
        label="Mật khẩu",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )


class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ["full_name", "username", "phone", "email", "password1", "password2"]
        labels = {"username": "Tên đăng nhập", "email": "Email"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["full_name"].required = True
        self.fields["phone"].required = True
        self.fields["email"].required = True
        self.fields["username"].help_text = "Chữ cái, chữ số và @/./+/-/_."


class BookingForm(forms.Form):
    branch = forms.ModelChoiceField(
        label="Chi nhánh", queryset=Branch.objects.filter(active=True), empty_label="Chọn chi nhánh"
    )
    services = forms.ModelMultipleChoiceField(
        label="Dịch vụ",
        queryset=Service.objects.filter(active=True),
        widget=forms.CheckboxSelectMultiple,
    )
    employee = forms.ModelChoiceField(
        label="Stylist",
        queryset=Employee.objects.filter(active=True, branch__active=True),
        empty_label="Chọn stylist",
    )
    date = forms.DateField(label="Ngày hẹn", widget=forms.DateInput(attrs={"type": "date"}))
    time = forms.TimeField(label="Giờ hẹn", input_formats=["%H:%M"], widget=forms.HiddenInput)
    note = forms.CharField(
        label="Lời nhắn cho stylist",
        required=False,
        max_length=500,
        widget=forms.Textarea(
            attrs={"rows": 3, "placeholder": "Ví dụ: tư vấn kiểu tóc phù hợp, giữ phần mái dài…"}
        ),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user and user.is_operator:
            customers = User.objects.filter(role=User.Role.CUSTOMER, is_active=True)
            if user.is_branch_staff:
                customers = customers.filter(appointments__branch_id=user.branch_id).distinct()
                self.fields["branch"].queryset = Branch.objects.filter(
                    pk=user.branch_id, active=True
                )
                self.fields["employee"].queryset = Employee.objects.filter(
                    branch_id=user.branch_id, active=True
                )
            self.fields["customer"] = forms.ModelChoiceField(
                label="Đặt cho khách hàng",
                queryset=customers.order_by("full_name"),
                empty_label="Chọn khách hàng",
            )
            self.fields["customer"].label_from_instance = lambda obj: (
                f"{obj.full_name} · {obj.phone}"
            )
        today = timezone.localdate()
        self.fields["date"].widget.attrs.update(
            {"min": today.isoformat(), "max": (today + timedelta(days=90)).isoformat()}
        )

    def clean(self):
        data = super().clean()
        if (
            data.get("employee")
            and data.get("branch")
            and data["employee"].branch_id != data["branch"].pk
        ):
            self.add_error("employee", "Stylist không thuộc chi nhánh đã chọn.")
        return data


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["rating", "comment"]
        widgets = {
            "rating": forms.Select(choices=[(i, f"{i} sao") for i in range(5, 0, -1)]),
            "comment": forms.Textarea(
                attrs={"rows": 3, "placeholder": "Chia sẻ trải nghiệm của bạn…"}
            ),
        }


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["full_name", "phone", "email"]
        labels = {"email": "Email"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in self.fields:
            self.fields[name].required = True


class BranchForm(forms.ModelForm):
    class Meta:
        model = Branch
        fields = ["name", "address", "phone", "opens_at", "closes_at", "active"]
        widgets = {
            name: forms.TimeInput(format="%H:%M", attrs={"type": "time"})
            for name in ["opens_at", "closes_at"]
        }

    def clean(self):
        data = super().clean()
        start, end = data.get("opens_at"), data.get("closes_at")
        if start and end and start >= end:
            raise forms.ValidationError("Giờ đóng cửa phải sau giờ mở cửa.")
        if self.instance.pk:
            appointments = Appointment.objects.filter(
                branch=self.instance, status__in=ACTIVE_STATUSES
            )
            if not data.get("active") and appointments.exists():
                raise forms.ValidationError(
                    "Chi nhánh còn lịch hẹn đang hoạt động. Hãy xử lý các lịch này trước khi tạm ngừng."
                )
            if start and end:
                if appointments.filter(
                    Q(start_at__time__lt=start) | Q(end_at__time__gt=end)
                ).exists():
                    raise forms.ValidationError("Giờ mới không bao phủ lịch hẹn đang hoạt động.")
                shifts = Shift.objects.filter(
                    employee__branch=self.instance, end_at__gte=timezone.now()
                )
                if shifts.filter(Q(start_at__time__lt=start) | Q(end_at__time__gt=end)).exists():
                    raise forms.ValidationError(
                        "Hãy điều chỉnh các ca làm sắp tới trước khi thu hẹp giờ mở cửa."
                    )
        return data


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ["name", "description", "kind", "price", "duration", "active"]
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ["name", "branch", "specialty", "bio", "active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["branch"].disabled = True
            self.fields[
                "branch"
            ].help_text = "Chi nhánh được giữ cố định để bảo toàn lịch sử phục vụ."

    def clean(self):
        data = super().clean()
        if (
            self.instance.pk
            and not data.get("active")
            and Appointment.objects.filter(
                employee=self.instance, status__in=ACTIVE_STATUSES
            ).exists()
        ):
            raise forms.ValidationError(
                "Stylist còn lịch hẹn đang hoạt động. Hãy xử lý các lịch này trước khi ngừng làm việc."
            )
        return data


class ChairForm(forms.ModelForm):
    class Meta:
        model = Chair
        fields = ["branch", "name", "active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["branch"].disabled = True
            self.fields["branch"].help_text = "Không chuyển ghế sang chi nhánh khác khi chỉnh sửa."

    def clean(self):
        data = super().clean()
        if self.instance.pk and self.instance.active and not data.get("active"):
            from .scheduling import peak_existing_capacity

            remaining = (
                Chair.objects.filter(branch=self.instance.branch, active=True)
                .exclude(pk=self.instance.pk)
                .count()
            )
            if peak_existing_capacity(self.instance.branch) > remaining:
                raise forms.ValidationError(
                    "Ngừng ghế sẽ làm chi nhánh thiếu sức chứa cho lịch đã nhận. Điều phối các lịch trước."
                )
        if (
            self.instance.pk
            and not data.get("active")
            and Appointment.objects.filter(chair=self.instance, status__in=ACTIVE_STATUSES).exists()
        ):
            raise forms.ValidationError("Ghế còn được phân cho lịch hẹn đang hoạt động.")
        return data


class ShiftForm(forms.ModelForm):
    class Meta:
        model = Shift
        fields = ["employee", "start_at", "end_at"]
        widgets = {
            name: forms.DateTimeInput(format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"})
            for name in ["start_at", "end_at"]
        }

    def clean(self):
        data = super().clean()
        employee, start, end = data.get("employee"), data.get("start_at"), data.get("end_at")
        if employee and start and end:
            s, e = timezone.localtime(start), timezone.localtime(end)
            if (
                start >= end
                or s.date() != e.date()
                or s.time() < employee.branch.opens_at
                or e.time() > employee.branch.closes_at
            ):
                # Exclude the invalid bound from model constraint validation;
                # PostgreSQL cannot construct a reversed TSTZRANGE.
                self.add_error(
                    "end_at",
                    "Ca làm phải có giờ kết thúc sau giờ bắt đầu và nằm trong giờ mở cửa của một ngày.",
                )
                return data
            if not employee.active or not employee.branch.active:
                self.add_error("employee", "Chọn stylist và chi nhánh đang hoạt động.")
                return data
            if (
                Shift.objects.filter(employee=employee, start_at__lt=end, end_at__gt=start)
                .exclude(pk=self.instance.pk)
                .exists()
            ):
                self.add_error("start_at", "Stylist đã có ca làm trùng khung giờ này.")
                return data
            if self.instance.pk:
                original = Shift.objects.get(pk=self.instance.pk)
                bookings = Appointment.objects.filter(
                    employee=original.employee,
                    status__in=ACTIVE_STATUSES,
                    start_at__gte=original.start_at,
                    end_at__lte=original.end_at,
                )
                if bookings.exists() and (
                    employee.pk != original.employee_id
                    or bookings.exclude(start_at__gte=start, end_at__lte=end).exists()
                ):
                    raise forms.ValidationError(
                        "Không được thay đổi ca làm khiến lịch hẹn đã đặt không còn được phục vụ."
                    )
        return data


class AccountForm(forms.ModelForm):
    new_password = forms.CharField(
        label="Mật khẩu mới",
        required=False,
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="Bắt buộc khi tạo tài khoản. Khi sửa, để trống nếu muốn giữ mật khẩu hiện tại.",
    )

    class Meta:
        model = User
        fields = ["username", "full_name", "phone", "email", "role", "branch", "is_active"]
        labels = {"username": "Tên đăng nhập", "email": "Email", "is_active": "Cho phép đăng nhập"}
        help_texts = {
            "username": "Chữ cái, chữ số và @/./+/-/_.",
            "is_active": "Bỏ chọn để khóa tài khoản.",
        }

    def __init__(self, *args, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor = actor
        self.original_role = self.instance.role
        self.original_active = self.instance.is_active
        self.fields["full_name"].required = True
        self.fields["new_password"].required = not self.instance.pk
        if actor and actor.pk == self.instance.pk:
            self.fields.pop("new_password")
            self.fields["role"].disabled = True
            self.fields["is_active"].disabled = True
            self.fields[
                "role"
            ].help_text = "Bạn không thể thay đổi vai trò hoặc khóa chính tài khoản đang đăng nhập."

    def clean(self):
        data = super().clean()
        if data.get("role") in (
            User.Role.RECEPTIONIST,
            User.Role.BRANCH_MANAGER,
            User.Role.STYLIST,
        ):
            if not data.get("branch") or not data["branch"].active:
                self.add_error(
                    "branch",
                    "Lễ tân cần một chi nhánh đang hoạt động."
                    if data.get("role") == User.Role.RECEPTIONIST
                    else "Nhân sự cần một chi nhánh đang hoạt động.",
                )
        else:
            data["branch"] = None
        if self.instance.pk:
            losing_manager = (
                self.original_role == User.Role.MANAGER
                and self.original_active
                and (data.get("role") != User.Role.MANAGER or not data.get("is_active"))
            )
            if (
                losing_manager
                and User.objects.filter(role=User.Role.MANAGER, is_active=True).count() <= 1
            ):
                raise forms.ValidationError(
                    "Hệ thống phải còn ít nhất một quản trị viên đang hoạt động."
                )
            if (
                self.original_role == User.Role.CUSTOMER
                and data.get("role") != User.Role.CUSTOMER
                and self.instance.appointments.exists()
            ):
                self.add_error(
                    "role", "Khách đã có lịch hẹn cần giữ vai trò khách hàng để bảo toàn lịch sử."
                )
        if self.instance.pk and hasattr(self.instance, "stylist_profile"):
            stylist = self.instance.stylist_profile
            if (
                data.get("role") != "stylist"
                or not data.get("branch")
                or data["branch"].pk != stylist.branch_id
            ):
                self.add_error(
                    "role", "Tài khoản đã gắn stylist phải giữ vai trò và chi nhánh tương ứng."
                )
        password = data.get("new_password")
        if password:
            from django.contrib.auth.password_validation import validate_password

            candidate = User(
                username=data.get("username", ""),
                full_name=data.get("full_name", ""),
                email=data.get("email", ""),
            )
            try:
                validate_password(password, candidate)
            except forms.ValidationError as error:
                self.add_error("new_password", error)
        return data

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data.get("new_password"):
            user.set_password(self.cleaned_data["new_password"])
        if commit:
            user.save()
        return user


class ConfirmDeleteForm(forms.Form):
    confirm = forms.BooleanField(label="Tôi xác nhận muốn xóa bản ghi này.", required=True)
