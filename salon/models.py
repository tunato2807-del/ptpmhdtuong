from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateTimeRangeField, RangeOperators
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.db import models
from django.db.models import Q, F, Func

phone_validator = RegexValidator(r'^0[0-9]{9}$', 'Số điện thoại gồm 10 chữ số, bắt đầu bằng 0.')

class Branch(models.Model):
    name = models.CharField('Tên chi nhánh', max_length=100, unique=True)
    address = models.CharField('Địa chỉ', max_length=250)
    phone = models.CharField('Điện thoại', max_length=10, validators=[phone_validator])
    opens_at = models.TimeField('Mở cửa')
    closes_at = models.TimeField('Đóng cửa')
    active = models.BooleanField('Đang hoạt động', default=True)
    class Meta:
        ordering = ['id']
        verbose_name = 'Chi nhánh'
        verbose_name_plural = 'Chi nhánh'
        constraints = [models.CheckConstraint(condition=Q(closes_at__gt=F('opens_at')), name='branch_hours_valid')]
    def __str__(self): return self.name

class User(AbstractUser):
    class Role(models.TextChoices):
        CUSTOMER = 'customer', 'Khách hàng'
        RECEPTIONIST = 'receptionist', 'Lễ tân'
        MANAGER = 'manager', 'Quản trị viên'
    full_name = models.CharField('Họ tên', max_length=100)
    phone = models.CharField('Số điện thoại', max_length=10, blank=True, validators=[phone_validator])
    role = models.CharField('Vai trò', max_length=20, choices=Role.choices, default=Role.CUSTOMER)
    branch = models.ForeignKey(Branch, null=True, blank=True, on_delete=models.PROTECT, verbose_name='Chi nhánh phụ trách')
    points = models.PositiveIntegerField('Điểm tích lũy', default=0)
    def __str__(self): return self.full_name or self.username
    @property
    def is_operator(self): return self.role in [self.Role.MANAGER, self.Role.RECEPTIONIST]
    @property
    def initials(self): return ''.join(w[0] for w in str(self).split()[-2:]).upper()

class Service(models.Model):
    class Kind(models.TextChoices):
        HAIR = 'hair', 'Cắt & tạo kiểu'
        CARE = 'care', 'Chăm sóc'
        COMBO = 'combo', 'Combo'
    name = models.CharField('Tên dịch vụ', max_length=100, unique=True)
    description = models.TextField('Mô tả', blank=True)
    kind = models.CharField('Nhóm', max_length=10, choices=Kind.choices, default=Kind.HAIR)
    price = models.PositiveIntegerField('Giá (VNĐ)', validators=[MinValueValidator(1000)])
    duration = models.PositiveIntegerField('Thời lượng (phút)', validators=[MinValueValidator(15), MaxValueValidator(240)])
    active = models.BooleanField('Cho phép đặt', default=True)
    class Meta:
        ordering = ['id']
        verbose_name = 'Dịch vụ / combo'
        verbose_name_plural = 'Dịch vụ / combo'
        constraints = [models.CheckConstraint(condition=Q(price__gte=1000, duration__gte=15, duration__lte=240), name='service_price_duration_valid')]
    def __str__(self): return self.name

class Employee(models.Model):
    name = models.CharField('Họ tên stylist', max_length=100)
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name='employees', verbose_name='Chi nhánh')
    specialty = models.CharField('Chuyên môn', max_length=150)
    bio = models.CharField('Giới thiệu', max_length=250, blank=True)
    active = models.BooleanField('Đang làm việc', default=True)
    class Meta:
        ordering = ['id']
        verbose_name = 'Stylist'
        verbose_name_plural = 'Stylist'
    def __str__(self): return self.name
    @property
    def initials(self): return ''.join(w[0] for w in self.name.split()[-2:]).upper()

class Chair(models.Model):
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name='chairs', verbose_name='Chi nhánh')
    name = models.CharField('Tên ghế', max_length=30)
    active = models.BooleanField('Sẵn sàng', default=True)
    class Meta:
        ordering = ['id']
        constraints = [models.UniqueConstraint(fields=['branch', 'name'], name='chair_branch_name_unique')]
        verbose_name = 'Ghế cắt'
        verbose_name_plural = 'Ghế cắt'
    def __str__(self): return f'{self.branch} · {self.name}'

class Shift(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name='shifts', verbose_name='Stylist')
    start_at = models.DateTimeField('Bắt đầu')
    end_at = models.DateTimeField('Kết thúc')
    class Meta:
        ordering = ['start_at']
        verbose_name = 'Ca làm việc'
        verbose_name_plural = 'Ca làm việc'
        constraints = [
            models.CheckConstraint(condition=Q(end_at__gt=F('start_at')), name='shift_positive_duration'),
            ExclusionConstraint(name='shift_no_overlap', expressions=[
                ('employee', RangeOperators.EQUAL),
                (Func('start_at', 'end_at', function='TSTZRANGE', output_field=DateTimeRangeField()), RangeOperators.OVERLAPS),
            ]),
        ]
    def __str__(self): return f'{self.employee} · {self.start_at:%d/%m/%Y}'

ACTIVE_STATUSES = ['booked', 'checked_in', 'in_service']

class Appointment(models.Model):
    class Status(models.TextChoices):
        BOOKED = 'booked', 'Đã đặt'
        CHECKED_IN = 'checked_in', 'Đã check-in'
        IN_SERVICE = 'in_service', 'Đang phục vụ'
        COMPLETED = 'completed', 'Hoàn thành'
        CANCELLED = 'cancelled', 'Đã hủy'
        NO_SHOW = 'no_show', 'Không đến'
    customer = models.ForeignKey(User, on_delete=models.PROTECT, related_name='appointments', verbose_name='Khách hàng')
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, verbose_name='Chi nhánh')
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, verbose_name='Stylist')
    chair = models.ForeignKey(Chair, on_delete=models.PROTECT, null=True, blank=True, verbose_name='Ghế cắt')
    start_at = models.DateTimeField('Bắt đầu')
    end_at = models.DateTimeField('Kết thúc')
    status = models.CharField('Trạng thái', max_length=20, choices=Status.choices, default=Status.BOOKED)
    note = models.CharField('Ghi chú', max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['start_at']
        verbose_name = 'Lịch hẹn'
        verbose_name_plural = 'Lịch hẹn'
        indexes = [models.Index(fields=['branch', 'start_at']), models.Index(fields=['customer', 'start_at'])]
        constraints = [
            models.CheckConstraint(condition=Q(end_at__gt=F('start_at')), name='appointment_positive_duration'),
            ExclusionConstraint(name='stylist_no_double_booking', expressions=[
                ('employee', RangeOperators.EQUAL),
                (Func('start_at', 'end_at', function='TSTZRANGE', output_field=DateTimeRangeField()), RangeOperators.OVERLAPS),
            ], condition=Q(status__in=ACTIVE_STATUSES)),
            ExclusionConstraint(name='chair_no_double_booking', expressions=[
                ('chair', RangeOperators.EQUAL),
                (Func('start_at', 'end_at', function='TSTZRANGE', output_field=DateTimeRangeField()), RangeOperators.OVERLAPS),
            ], condition=Q(status__in=ACTIVE_STATUSES, chair__isnull=False)),
        ]
    @property
    def code(self): return f'LH{self.pk:05d}'
    @property
    def total(self): return sum(item.price for item in self.items.all())
    def __str__(self): return self.code

class AppointmentItem(models.Model):
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='items')
    service = models.ForeignKey(Service, on_delete=models.PROTECT)
    name = models.CharField(max_length=100)
    price = models.PositiveIntegerField()
    duration = models.PositiveIntegerField()
    class Meta:
        constraints = [models.UniqueConstraint(fields=['appointment', 'service'], name='appointment_service_unique')]

class Invoice(models.Model):
    class Method(models.TextChoices):
        CASH = 'cash', 'Tiền mặt'
        MOCK = 'mock', 'Thẻ mô phỏng'
    appointment = models.OneToOneField(Appointment, on_delete=models.PROTECT, related_name='invoice')
    total = models.PositiveIntegerField('Tổng thanh toán')
    method = models.CharField('Phương thức', max_length=10, choices=Method.choices)
    paid_at = models.DateTimeField('Thanh toán lúc', auto_now_add=True)
    cashier = models.ForeignKey(User, on_delete=models.PROTECT)
    class Meta:
        verbose_name = 'Hóa đơn đã thanh toán'
        verbose_name_plural = 'Hóa đơn đã thanh toán'
    @property
    def code(self): return f'HD{self.pk:05d}'

class Review(models.Model):
    appointment = models.OneToOneField(Appointment, on_delete=models.PROTECT, related_name='review')
    rating = models.PositiveSmallIntegerField('Số sao', validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.CharField('Bình luận', max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.CheckConstraint(condition=Q(rating__gte=1, rating__lte=5), name='review_rating_valid')]

class Notification(models.Model):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.CharField(max_length=250)
    created_at = models.DateTimeField(auto_now_add=True)

class AuditLog(models.Model):
    actor = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    appointment = models.ForeignKey(Appointment, null=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
