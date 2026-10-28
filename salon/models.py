from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateTimeRangeField, RangeOperators
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.db import models
from django.db.models import Q, F, Func

phone_validator = RegexValidator(r'^0[0-9]{9}$', 'Số điện thoại gồm 10 chữ số, bắt đầu bằng 0.')

def _database_column(inherited_field, column):
    """Preserve Django auth field definitions while naming the SQL column in Vietnamese."""
    field = inherited_field.clone()
    field.db_column = column
    return field

class Branch(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID', db_column='machinhanh')
    name = models.CharField('Tên chi nhánh', max_length=100, unique=True, db_column='tenchinhanh')
    address = models.CharField('Địa chỉ', max_length=250, db_column='diachi')
    phone = models.CharField('Điện thoại', max_length=10, validators=[phone_validator], db_column='sodienthoai')
    opens_at = models.TimeField('Mở cửa', db_column='giomocua')
    closes_at = models.TimeField('Đóng cửa', db_column='giodongcua')
    active = models.BooleanField('Đang hoạt động', default=True, db_column='hoatdong')
    booking_days = models.PositiveSmallIntegerField('Số ngày cho đặt trước', default=30, validators=[MinValueValidator(1), MaxValueValidator(90)], db_column='songaydatruoc')
    cancel_hours = models.PositiveSmallIntegerField('Hạn đổi/hủy trước giờ hẹn', default=2, validators=[MaxValueValidator(48)], db_column='giohuytruoc')
    late_minutes = models.PositiveSmallIntegerField('Số phút chờ khách muộn', default=15, validators=[MaxValueValidator(120)], db_column='phutdenmuon')
    class Meta:
        ordering = ['id']
        verbose_name = 'Chi nhánh'
        verbose_name_plural = 'Chi nhánh'
        constraints = [models.CheckConstraint(condition=Q(closes_at__gt=F('opens_at')), name='branch_hours_valid')]
    def __str__(self): return self.name

class User(AbstractUser):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID', db_column='manguoidung')
    password = _database_column(AbstractUser._meta.get_field('password'), 'matkhau')
    last_login = _database_column(AbstractUser._meta.get_field('last_login'), 'landangnhapcuoi')
    is_superuser = _database_column(AbstractUser._meta.get_field('is_superuser'), 'laquantri')
    username = _database_column(AbstractUser._meta.get_field('username'), 'tendangnhap')
    first_name = _database_column(AbstractUser._meta.get_field('first_name'), 'ten')
    last_name = _database_column(AbstractUser._meta.get_field('last_name'), 'ho')
    email = _database_column(AbstractUser._meta.get_field('email'), 'thudientu')
    is_staff = _database_column(AbstractUser._meta.get_field('is_staff'), 'lanhanvien')
    is_active = _database_column(AbstractUser._meta.get_field('is_active'), 'hoatdong')
    date_joined = _database_column(AbstractUser._meta.get_field('date_joined'), 'ngaythamgia')
    class Role(models.TextChoices):
        CUSTOMER = 'customer', 'Khách hàng'
        RECEPTIONIST = 'receptionist', 'Lễ tân'
        MANAGER = 'manager', 'Quản trị toàn chuỗi'
        BRANCH_MANAGER = 'branch_manager', 'Quản lý chi nhánh'
        STYLIST = 'stylist', 'Tài khoản stylist'
    full_name = models.CharField('Họ tên', max_length=100, db_column='hoten')
    phone = models.CharField('Số điện thoại', max_length=10, blank=True, validators=[phone_validator], db_column='sodienthoai')
    role = models.CharField('Vai trò', max_length=20, choices=Role.choices, default=Role.CUSTOMER, db_column='vaitro')
    branch = models.ForeignKey(Branch, null=True, blank=True, on_delete=models.PROTECT, verbose_name='Chi nhánh phụ trách', db_column='machinhanh')
    points_debt = models.PositiveIntegerField('Điểm cần thu hồi', default=0, db_column='diemcanthuhoi')
    points = models.PositiveIntegerField('Điểm tích lũy', default=0, db_column='diemtichluy')
    def __str__(self): return self.full_name or self.username
    @property
    def is_operator(self): return self.role in [self.Role.MANAGER, self.Role.BRANCH_MANAGER, self.Role.RECEPTIONIST]
    @property
    def is_manager(self): return self.role == self.Role.MANAGER
    @property
    def is_branch_staff(self): return self.role in [self.Role.RECEPTIONIST, self.Role.BRANCH_MANAGER, self.Role.STYLIST]
    @property
    def is_branch_manager(self): return self.role == self.Role.BRANCH_MANAGER
    @property
    def can_manage_branch(self): return self.role in [self.Role.MANAGER, self.Role.BRANCH_MANAGER]
    @property
    def is_stylist(self): return self.role == self.Role.STYLIST
    @property
    def initials(self): return ''.join(w[0] for w in str(self).split()[-2:]).upper()

class Service(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID', db_column='madichvu')
    class Kind(models.TextChoices):
        HAIR = 'hair', 'Cắt & tạo kiểu'
        CARE = 'care', 'Chăm sóc'
        COMBO = 'combo', 'Combo'
    name = models.CharField('Tên dịch vụ', max_length=100, unique=True, db_column='tendichvu')
    description = models.TextField('Mô tả', blank=True, db_column='mota')
    kind = models.CharField('Nhóm', max_length=10, choices=Kind.choices, default=Kind.HAIR, db_column='loaidichvu')
    price = models.PositiveIntegerField('Giá (VNĐ)', validators=[MinValueValidator(1000)], db_column='giatien')
    duration = models.PositiveIntegerField('Thời lượng (phút)', validators=[MinValueValidator(15), MaxValueValidator(240)], db_column='thoiluong')
    active = models.BooleanField('Cho phép đặt', default=True, db_column='hoatdong')
    class Meta:
        ordering = ['id']
        verbose_name = 'Dịch vụ / combo'
        verbose_name_plural = 'Dịch vụ / combo'
        constraints = [models.CheckConstraint(condition=Q(price__gte=1000, duration__gte=15, duration__lte=240), name='service_price_duration_valid')]
    def __str__(self): return self.name

class Employee(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID', db_column='manhanvien')
    name = models.CharField('Họ tên stylist', max_length=100, db_column='hoten')
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name='employees', verbose_name='Chi nhánh', db_column='machinhanh')
    specialty = models.CharField('Chuyên môn', max_length=150, db_column='chuyenmon')
    bio = models.CharField('Giới thiệu', max_length=250, blank=True, db_column='gioithieu')
    account = models.OneToOneField(User, null=True, blank=True, on_delete=models.PROTECT, related_name='stylist_profile', db_column='mataikhoan')
    commission_percent = models.PositiveSmallIntegerField('Hoa hồng (%)', default=0, validators=[MaxValueValidator(100)], db_column='phantramhoahong')
    active = models.BooleanField('Đang làm việc', default=True, db_column='hoatdong')
    class Meta:
        ordering = ['id']
        verbose_name = 'Stylist'
        verbose_name_plural = 'Stylist'
    def __str__(self): return self.name
    @property
    def initials(self): return ''.join(w[0] for w in self.name.split()[-2:]).upper()

class Chair(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID', db_column='maghe')
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name='chairs', verbose_name='Chi nhánh', db_column='machinhanh')
    name = models.CharField('Tên ghế', max_length=30, db_column='tenghe')
    active = models.BooleanField('Sẵn sàng', default=True, db_column='hoatdong')
    class Meta:
        ordering = ['id']
        constraints = [models.UniqueConstraint(fields=['branch', 'name'], name='chair_branch_name_unique')]
        verbose_name = 'Ghế cắt'
        verbose_name_plural = 'Ghế cắt'
    def __str__(self): return f'{self.branch} · {self.name}'

class Shift(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID', db_column='macalam')
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name='shifts', verbose_name='Stylist', db_column='manhanvien')
    start_at = models.DateTimeField('Bắt đầu', db_column='thoigianbatdau')
    end_at = models.DateTimeField('Kết thúc', db_column='thoigianketthuc')
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
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID', db_column='malichhen')
    class Status(models.TextChoices):
        BOOKED = 'booked', 'Đã đặt'
        CHECKED_IN = 'checked_in', 'Đã check-in'
        IN_SERVICE = 'in_service', 'Đang phục vụ'
        AWAITING_PAYMENT = 'awaiting_payment', 'Chờ thanh toán'
        COMPLETED = 'completed', 'Đã thanh toán'
        CANCELLED = 'cancelled', 'Đã hủy'
        NO_SHOW = 'no_show', 'Không đến'
    customer = models.ForeignKey(User, on_delete=models.PROTECT, related_name='appointments', verbose_name='Khách hàng', db_column='makhachhang')
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, verbose_name='Chi nhánh', db_column='machinhanh')
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, verbose_name='Stylist', db_column='manhanvien')
    chair = models.ForeignKey(Chair, on_delete=models.PROTECT, null=True, blank=True, verbose_name='Ghế cắt', db_column='maghe')
    start_at = models.DateTimeField('Bắt đầu', db_column='thoigianbatdau')
    end_at = models.DateTimeField('Kết thúc', db_column='thoigianketthuc')
    status = models.CharField('Trạng thái', max_length=20, choices=Status.choices, default=Status.BOOKED, db_column='trangthai')
    note = models.CharField('Ghi chú', max_length=500, blank=True, db_column='ghichu')
    checked_in_at = models.DateTimeField(null=True, blank=True, db_column='giokhachden')
    service_started_at = models.DateTimeField(null=True, blank=True, db_column='giophucvu')
    service_finished_at = models.DateTimeField(null=True, blank=True, db_column='gioxongdichvu')
    source = models.CharField(max_length=12, default='web', choices=[('web','Website'),('walkin','Tại quầy')], db_column='nguondat')
    created_at = models.DateTimeField(auto_now_add=True, db_column='ngaytao')
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
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID', db_column='machitiet')
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='items', db_column='malichhen')
    service = models.ForeignKey(Service, on_delete=models.PROTECT, db_column='madichvu')
    name = models.CharField(max_length=100, db_column='tendichvu')
    price = models.PositiveIntegerField(db_column='giatien')
    duration = models.PositiveIntegerField(db_column='thoiluong')
    class Meta:
        constraints = [models.UniqueConstraint(fields=['appointment', 'service'], name='appointment_service_unique')]

class Invoice(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID', db_column='mahoadon')
    class Method(models.TextChoices):
        CASH = 'cash', 'Tiền mặt'
        MOCK = 'mock', 'Thẻ mô phỏng'
    appointment = models.OneToOneField(Appointment, on_delete=models.PROTECT, related_name='invoice', db_column='malichhen')
    total = models.PositiveIntegerField('Tổng thanh toán', db_column='tongthanhtoan')
    discount = models.PositiveIntegerField('Giảm từ điểm (VNĐ)', default=0, db_column='tiengiam')
    points_earned = models.PositiveIntegerField(default=0, db_column='diemdatich')
    points_debt_paid = models.PositiveIntegerField(default=0, db_column='diemdathuhoi')
    voucher_discount = models.PositiveIntegerField('Giảm voucher', default=0, db_column='giamvoucher')
    voucher_code = models.CharField(max_length=40, blank=True, db_column='mavoucher')
    points_used = models.PositiveIntegerField('Điểm đã dùng', default=0, db_column='diemdadung')
    method = models.CharField('Phương thức', max_length=10, choices=Method.choices, db_column='phuongthucthanhtoan')
    paid_at = models.DateTimeField('Thanh toán lúc', auto_now_add=True, db_column='thoigianthanhtoan')
    cashier = models.ForeignKey(User, on_delete=models.PROTECT, db_column='mathungan')
    class Meta:
        constraints = [models.CheckConstraint(condition=Q(discount=F('points_used') * 1000), name='invoice_points_discount'), models.CheckConstraint(condition=Q(discount__lte=(F('total') + F('discount') + F('voucher_discount')) / 5), name='invoice_discount_limit')]
        verbose_name = 'Hóa đơn đã thanh toán'
        verbose_name_plural = 'Hóa đơn đã thanh toán'
    @property
    def code(self): return f'HD{self.pk:05d}'
    @property
    def subtotal(self): return self.total + self.discount + self.voucher_discount

class Review(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID', db_column='madanhgia')
    appointment = models.OneToOneField(Appointment, on_delete=models.PROTECT, related_name='review', db_column='malichhen')
    rating = models.PositiveSmallIntegerField('Số sao', validators=[MinValueValidator(1), MaxValueValidator(5)], db_column='sosao')
    comment = models.CharField('Bình luận', max_length=500, blank=True, db_column='binhluan')
    created_at = models.DateTimeField(auto_now_add=True, db_column='ngaytao')
    class Meta:
        constraints = [models.CheckConstraint(condition=Q(rating__gte=1, rating__lte=5), name='review_rating_valid')]

class Notification(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID', db_column='mathongbao')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', db_column='manguoinhan')
    appointment = models.ForeignKey(Appointment, null=True, blank=True, on_delete=models.SET_NULL, db_column='malichhen')
    read_at = models.DateTimeField(null=True, blank=True, db_column='ngaydoc')
    message = models.CharField(max_length=250, db_column='noidung')
    created_at = models.DateTimeField(auto_now_add=True, db_column='ngaytao')

class AuditLog(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID', db_column='manhatky')
    actor = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, db_column='manguoithaotac')
    appointment = models.ForeignKey(Appointment, null=True, on_delete=models.SET_NULL, db_column='malichhen')
    branch = models.ForeignKey(Branch, null=True, blank=True, on_delete=models.PROTECT, db_column='machinhanh')
    action = models.CharField(max_length=100, db_column='hanhdong')
    created_at = models.DateTimeField(auto_now_add=True, db_column='ngaytao')


class PointEntry(models.Model):
    class Kind(models.TextChoices):
        OPENING = 'opening', 'Số dư chuyển tiếp'
        EARNED = 'earned', 'Tích điểm thanh toán'
        REDEEMED = 'redeemed', 'Sử dụng điểm'
        REFUND = 'refund', 'Điều chỉnh hoàn tiền'
        DEBT_RECOVERY = 'debt_recovery', 'Đối trừ điểm cần thu hồi'
    id = models.BigAutoField(primary_key=True, db_column='mabiendong')
    customer = models.ForeignKey(User, on_delete=models.PROTECT, related_name='point_entries', db_column='makhachhang')
    invoice = models.ForeignKey(Invoice, null=True, blank=True, on_delete=models.PROTECT, db_column='mahoadon')
    kind = models.CharField(max_length=20, choices=Kind.choices, db_column='loai')
    amount = models.IntegerField(db_column='sodiem')
    balance = models.PositiveIntegerField(db_column='sodusaubiendong')
    created_at = models.DateTimeField(auto_now_add=True, db_column='ngaytao')
    class Meta:
        ordering = ['-created_at', '-pk']
        constraints = [
            models.UniqueConstraint(fields=['invoice', 'kind'], condition=Q(invoice__isnull=False), name='points_invoice_kind_unique'),
            models.UniqueConstraint(fields=['customer'], condition=Q(kind='opening'), name='points_opening_unique'),
            models.CheckConstraint(condition=Q(kind__in=['redeemed','debt_recovery'], amount__lt=0) | Q(kind__in=['opening','earned'], amount__gte=0) | Q(kind='refund'), name='points_amount_sign'),
        ]


class EmployeeAbsence(models.Model):
    id = models.BigAutoField(primary_key=True, db_column='manghiphep')
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name='absences', db_column='manhanvien')
    start_at = models.DateTimeField(db_column='batdau')
    end_at = models.DateTimeField(db_column='ketthuc')
    reason = models.CharField(max_length=250, db_column='lydo')
    actor = models.ForeignKey(User, on_delete=models.PROTECT, db_column='manguoitao')
    active = models.BooleanField(default=True, db_column='hieuluc')
    class Meta:
        constraints = [models.CheckConstraint(condition=Q(end_at__gt=F('start_at')), name='absence_valid_period')]


class BranchClosure(models.Model):
    id = models.BigAutoField(primary_key=True, db_column='malichnghi')
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name='closures', db_column='machinhanh')
    start_at = models.DateTimeField(db_column='batdau')
    end_at = models.DateTimeField(db_column='ketthuc')
    reason = models.CharField(max_length=250, db_column='lydo')
    active = models.BooleanField(default=True, db_column='hieuluc')
    class Meta:
        constraints = [models.CheckConstraint(condition=Q(end_at__gt=F('start_at')), name='closure_valid_period')]


class AppointmentChange(models.Model):
    id = models.BigAutoField(primary_key=True, db_column='mabienchuyen')
    appointment = models.ForeignKey(Appointment, on_delete=models.PROTECT, related_name='changes', db_column='malichhen')
    actor = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, db_column='manguoithuchien')
    action = models.CharField(max_length=40, db_column='thaotac')
    reason = models.CharField(max_length=250, db_column='lydo')
    before = models.JSONField(default=dict, db_column='truockhisua')
    after = models.JSONField(default=dict, db_column='saukhisua')
    created_at = models.DateTimeField(auto_now_add=True, db_column='ngaytao')
    class Meta:
        ordering = ['-created_at', '-pk']


class EmailOutbox(models.Model):
    id = models.BigAutoField(primary_key=True, db_column='mathugui')
    appointment = models.ForeignKey(Appointment, on_delete=models.PROTECT, db_column='malichhen')
    key = models.CharField(max_length=180, unique=True, db_column='khoagui')
    recipient = models.EmailField(db_column='emailnhan')
    subject = models.CharField(max_length=200, db_column='tieude')
    body = models.TextField(db_column='noidung')
    due_at = models.DateTimeField(db_column='giogui')
    sent_at = models.DateTimeField(null=True, blank=True, db_column='daguiluc')
    cancelled = models.BooleanField(default=False, db_column='dahuy')
    attempts = models.PositiveSmallIntegerField(default=0, db_column='solanthu')
    last_error = models.CharField(max_length=200, blank=True, db_column='loicuoi')
    class Meta:
        indexes = [models.Index(fields=['sent_at', 'cancelled', 'due_at'])]


class Voucher(models.Model):
    id = models.BigAutoField(primary_key=True, db_column='mauudai')
    code = models.CharField('Mã voucher', max_length=40, unique=True, db_column='mavoucher')
    branch = models.ForeignKey(Branch, null=True, blank=True, on_delete=models.PROTECT, db_column='machinhanh')
    amount = models.PositiveIntegerField('Giảm cố định (đ)', db_column='sotiengiam')
    min_total = models.PositiveIntegerField('Hóa đơn tối thiểu', default=0, db_column='toithieu')
    starts_at = models.DateTimeField('Bắt đầu', db_column='batdau')
    ends_at = models.DateTimeField('Kết thúc', db_column='ketthuc')
    max_uses = models.PositiveIntegerField('Lượt sử dụng tối đa', default=100, db_column='luottoida')
    active = models.BooleanField('Đang áp dụng', default=True, db_column='hoatdong')
    class Meta:
        constraints = [models.CheckConstraint(condition=Q(amount__gt=0, max_uses__gt=0, ends_at__gt=F('starts_at')), name='voucher_valid')]
    def __str__(self): return self.code


class VoucherUse(models.Model):
    id = models.BigAutoField(primary_key=True, db_column='maluotdung')
    voucher = models.ForeignKey(Voucher, on_delete=models.PROTECT, related_name='uses', db_column='mauudai')
    invoice = models.OneToOneField(Invoice, on_delete=models.PROTECT, db_column='mahoadon')
    customer = models.ForeignKey(User, on_delete=models.PROTECT, db_column='makhachhang')
    class Meta:
        constraints = [models.UniqueConstraint(fields=['voucher', 'customer'], name='voucher_once_per_customer')]


class Product(models.Model):
    id = models.BigAutoField(primary_key=True, db_column='masanpham')
    sku = models.CharField('Mã sản phẩm', max_length=40, unique=True, db_column='makho')
    name = models.CharField('Tên sản phẩm / vật tư', max_length=150, db_column='tensanpham')
    unit = models.CharField('Đơn vị', max_length=30, default='chai', db_column='donvi')
    reorder_level = models.PositiveIntegerField('Ngưỡng cảnh báo tồn', default=5, db_column='nguongton')
    active = models.BooleanField('Đang sử dụng', default=True, db_column='hoatdong')
    def __str__(self): return f'{self.sku} · {self.name}'


class Stock(models.Model):
    id = models.BigAutoField(primary_key=True, db_column='matonkho')
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, db_column='machinhanh')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, db_column='masanpham')
    quantity = models.PositiveIntegerField(default=0, db_column='soluongton')
    class Meta:
        constraints = [models.UniqueConstraint(fields=['branch', 'product'], name='stock_per_branch')]


class StockMovement(models.Model):
    id = models.BigAutoField(primary_key=True, db_column='mabiendongkho')
    stock = models.ForeignKey(Stock, on_delete=models.PROTECT, related_name='movements', db_column='matonkho')
    amount = models.IntegerField(db_column='soluong')
    balance = models.PositiveIntegerField(db_column='tonsau')
    kind = models.CharField(max_length=12, choices=[('receipt','Nhập kho'),('consume','Xuất sử dụng'),('adjust','Kiểm kê'),('transfer','Chuyển kho')], db_column='loai')
    reference = models.CharField(max_length=40, blank=True, db_column='maphieu')
    reason = models.CharField(max_length=250, db_column='lydo')
    actor = models.ForeignKey(User, on_delete=models.PROTECT, db_column='manguoitao')
    created_at = models.DateTimeField(auto_now_add=True, db_column='ngaytao')
    class Meta:
        ordering = ['-created_at', '-pk']
        constraints = [models.CheckConstraint(condition=~Q(amount=0), name='stock_nonzero_movement')]


class Commission(models.Model):
    id = models.BigAutoField(primary_key=True, db_column='mahoahong')
    invoice = models.OneToOneField(Invoice, on_delete=models.PROTECT, db_column='mahoadon')
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, db_column='manhanvien')
    percent = models.PositiveSmallIntegerField(db_column='tyle')
    amount = models.PositiveIntegerField(db_column='sotien')
    created_at = models.DateTimeField(auto_now_add=True, db_column='ngaytao')
    class Meta:
        constraints = [models.CheckConstraint(condition=Q(percent__lte=100), name='commission_rate_valid')]


class Refund(models.Model):
    id = models.BigAutoField(primary_key=True, db_column='mahoantien')
    invoice = models.OneToOneField(Invoice, on_delete=models.PROTECT, related_name='refund', db_column='mahoadon')
    amount = models.PositiveIntegerField(db_column='sotienhoan')
    points_debt_added = models.PositiveIntegerField(default=0, db_column='diemthieuthuhoi')
    points_debt_repaid = models.PositiveIntegerField(default=0, db_column='diemhoandadoitru')
    reason = models.CharField(max_length=250, db_column='lydo')
    actor = models.ForeignKey(User, on_delete=models.PROTECT, db_column='manguoithuchien')
    created_at = models.DateTimeField(auto_now_add=True, db_column='ngaytao')


class AuthRateBucket(models.Model):
    """Shared short-lived counters. Keys are keyed hashes, never raw contacts/IPs."""
    key=models.CharField(primary_key=True,max_length=64,db_column='makhoa')
    expires_at=models.DateTimeField(db_index=True,db_column='thoigianhethan')
    count=models.PositiveIntegerField(default=0,db_column='solan')


class DailyClosing(models.Model):
    id = models.BigAutoField(primary_key=True, db_column='machotso')
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, db_column='machinhanh')
    day = models.DateField(db_column='ngay')
    expected_cash = models.IntegerField(db_column='tienmathethong')
    counted_cash = models.PositiveIntegerField(db_column='tienmatthucte')
    invoices_count = models.PositiveIntegerField(db_column='sohoadon')
    reason = models.CharField(max_length=250, blank=True, db_column='ghichu')
    actor = models.ForeignKey(User, on_delete=models.PROTECT, db_column='manguoichot')
    created_at = models.DateTimeField(auto_now_add=True, db_column='ngaytao')
    class Meta:
        constraints = [models.UniqueConstraint(fields=['branch', 'day'], name='closing_once_per_branch_day')]
