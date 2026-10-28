"""Transactional application layer. All schedule mutations serialize on the branch.

PostgreSQL exclusion constraints also protect against bypasses of this layer.
Times are aware datetimes; intervals are half open [start, end).
"""
from datetime import datetime, timedelta
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone
from .models import (Branch, Employee, Service, Shift, Appointment, AppointmentItem,
                     Chair, Invoice, User, PointEntry, ACTIVE_STATUSES)
from .events import publisher, AppointmentEvent

def local_at(day, clock):
    return timezone.make_aware(datetime.combine(day, clock))

def assert_operator(actor, branch_id):
    if not actor.is_authenticated:
        raise PermissionDenied
    current=User.objects.filter(pk=actor.pk,is_active=True).first()
    if not current or not current.is_operator or (current.is_branch_staff and current.branch_id!=branch_id):
        raise PermissionDenied
    return current


def emit(appointment, actor, message):
    publisher.publish(AppointmentEvent(appointment, actor, message))

def validate_slot(branch, employee, start, duration, now=None, exclude_id=None, allow_past=False):
    now = now or timezone.now()
    end = start + timedelta(minutes=duration)
    day = timezone.localdate(start)
    today = timezone.localdate(now)
    if not branch.active or not employee.active or employee.branch_id != branch.pk:
        raise ValidationError('Stylist không thuộc chi nhánh đang hoạt động.')
    if day < today or day > today + timedelta(days=branch.booking_days) or (start < now and not allow_past):
        raise ValidationError(f'Chọn thời gian trong tương lai, tối đa {branch.booking_days} ngày tới.')
    if start.minute not in (0, 15, 30, 45) or start.second or start.microsecond:
        raise ValidationError('Giờ hẹn phải theo bước 15 phút.')
    if start < local_at(day, branch.opens_at) or end > local_at(day, branch.closes_at):
        raise ValidationError('Dịch vụ phải kết thúc trong giờ mở cửa.')
    if not Shift.objects.filter(employee=employee, start_at__lte=start, end_at__gte=end).exists():
        raise ValidationError('Stylist không có ca làm việc trong khung giờ này.')
    if Appointment.objects.filter(employee=employee, status__in=ACTIVE_STATUSES,
                                  start_at__lt=end, end_at__gt=start).exclude(pk=exclude_id).exists():
        raise ValidationError('Khung giờ vừa được đặt. Vui lòng chọn giờ khác.')
    from .scheduling import validate_resources
    validate_resources(branch, employee, start, end, exclude_id)
    return end

def available_slots(branch, employee, day, duration, exclude_id=None):
    from .scheduling import day_slots
    return day_slots(branch,employee,day,duration,exclude_id)

@transaction.atomic
def book(*, customer, branch_id, employee_id, service_ids, start, note='', actor=None, source='web'):
    actor = actor or customer
    if actor.pk != customer.pk:
        assert_operator(actor, branch_id)
    if customer.role != User.Role.CUSTOMER or not customer.is_active:
        raise ValidationError('Chọn tài khoản khách hàng đang hoạt động.')
    branch = Branch.objects.select_for_update().get(pk=branch_id)
    if actor.pk != customer.pk:assert_operator(actor,branch_id)
    employee = Employee.objects.get(pk=employee_id)
    selected = list(Service.objects.filter(pk__in=set(service_ids), active=True).order_by('pk'))
    if not selected or len(selected) != len(set(service_ids)):
        raise ValidationError('Dịch vụ không còn khả dụng.')
    duration = sum(s.duration for s in selected)
    if duration > 480:
        raise ValidationError('Tổng thời lượng không được quá 8 giờ.')
    end = validate_slot(branch, employee, start, duration)
    if Appointment.objects.filter(customer=customer, status__in=ACTIVE_STATUSES,
                                  start_at__lt=end, end_at__gt=start).exists():
        raise ValidationError('Bạn đã có lịch hẹn trùng thời gian này.')
    # Serialize per-customer too, preventing concurrent bookings across branches.
    current_customer = User.objects.select_for_update().get(pk=customer.pk)
    if current_customer.role != User.Role.CUSTOMER or not current_customer.is_active:
        raise ValidationError('Chọn tài khoản khách hàng đang hoạt động.')
    if Appointment.objects.filter(customer=customer, status__in=ACTIVE_STATUSES,
                                  start_at__lt=end, end_at__gt=start).exists():
        raise ValidationError('Bạn đã có lịch hẹn trùng thời gian này.')
    appointment = Appointment.objects.create(customer=customer, branch=branch, employee=employee,
        start_at=start, end_at=end, note=note[:500], source=source)
    AppointmentItem.objects.bulk_create([AppointmentItem(appointment=appointment, service=s,
        name=s.name, price=s.price, duration=s.duration) for s in selected])
    emit(appointment, actor, 'Đặt lịch thành công')
    return appointment

class CashPayment:
    method = Invoice.Method.CASH
    def validate(self, confirmation): return None

class MockPayment:
    method = Invoice.Method.MOCK
    def validate(self, confirmation):
        if confirmation != 'confirmed':
            raise ValidationError('Cần xác nhận giao dịch mô phỏng. Không phát sinh giao dịch ngân hàng.')

class PaymentFactory:
    @staticmethod
    def create(method):
        strategies = {'cash': CashPayment, 'mock': MockPayment}
        if method not in strategies:
            raise ValidationError('Phương thức thanh toán không hợp lệ.')
        return strategies[method]()

@transaction.atomic
def transition(*, pk, actor, action, chair_id=None, method='cash', confirmation='', redeem_points=0, voucher_code='', reason='', quoted_total=None):
    original = Appointment.objects.get(pk=pk)
    is_owner = actor.pk == original.customer_id
    stylist_action = actor.is_stylist and action in ('start', 'finish') and Employee.objects.filter(pk=original.employee_id, account=actor, active=True, branch_id=actor.branch_id).exists()
    if not stylist_action and (not is_owner or action != 'cancel'):
        assert_operator(actor, original.branch_id)
    Branch.objects.select_for_update().get(pk=original.branch_id)
    a = Appointment.objects.select_for_update().get(pk=pk)
    if stylist_action:
        if not User.objects.filter(pk=actor.pk,is_active=True,role='stylist',branch_id=a.branch_id).exists():raise PermissionDenied
    elif not is_owner or action!='cancel':assert_operator(actor,a.branch_id)
    now = timezone.now()
    from .business import snapshot, record_change
    before = snapshot(a)
    if action == 'cancel':
        if a.status != Appointment.Status.BOOKED:
            raise ValidationError('Chỉ có thể hủy lịch chưa check-in.')
        if not actor.is_operator and a.start_at - now < timedelta(hours=a.branch.cancel_hours):
            raise ValidationError(f'Bạn chỉ có thể hủy trước giờ hẹn ít nhất {a.branch.cancel_hours} giờ. Vui lòng gọi chi nhánh.')
        a.status = Appointment.Status.CANCELLED
        message = 'Đã hủy lịch hẹn'
    elif action == 'checkin':
        if a.status != Appointment.Status.BOOKED:
            raise ValidationError('Lịch này không thể check-in.')
        if timezone.localdate(a.start_at) != timezone.localdate():
            raise ValidationError('Chỉ check-in lịch hẹn trong ngày hôm nay.')
        chair = Chair.objects.filter(pk=chair_id, branch=a.branch, active=True).first()
        if chair is None:
            raise ValidationError('Chọn ghế hợp lệ thuộc chi nhánh.')
        busy = Appointment.objects.filter(chair=chair).exclude(pk=a.pk).filter(
            Q(status__in=['checked_in', 'in_service']) |
            Q(status__in=ACTIVE_STATUSES, start_at__lt=a.end_at, end_at__gt=a.start_at))
        if busy.exists():
            raise ValidationError('Ghế đang được sử dụng. Vui lòng chọn ghế khác.')
        if a.start_at + timedelta(minutes=a.branch.late_minutes) < now and not reason.strip():
            raise ValidationError('Khách đến muộn. Nhập lý do và xác nhận lại khả năng phục vụ.')
        if now < a.start_at - timedelta(minutes=15):
            raise ValidationError('Chỉ check-in sớm tối đa 15 phút. Khách đến sớm vui lòng chờ.')
        if now > a.start_at:
            proposed_end = max(a.end_at, now + timedelta(minutes=sum(i.duration for i in a.items.all())))
            minutes = int((proposed_end-a.start_at).total_seconds()/60)+1
            if minutes>480:
                raise ValidationError('Đã quá xa giờ hẹn. Hãy đổi lịch sang khung giờ thực tế.')
            a.end_at=validate_slot(a.branch,a.employee,a.start_at,minutes,exclude_id=a.pk,allow_past=True)
        from .scheduling import validate_resources
        validate_resources(a.branch,a.employee,a.start_at,a.end_at,a.pk)
        a.checked_in_at = now
        a.chair = chair
        a.status = Appointment.Status.CHECKED_IN
        message = f'Check-in tại {chair.name}'
    elif action == 'release_checkin':
        if a.status!=Appointment.Status.CHECKED_IN or not reason.strip():
            raise ValidationError('Chỉ trả khách đã check-in về chờ điều phối, bắt buộc lý do.')
        a.chair=None;a.checked_in_at=None;a.status=Appointment.Status.BOOKED
        message='Trả lịch về chờ điều phối, đã giải phóng ghế'
    elif action == 'start':
        if a.status != Appointment.Status.CHECKED_IN:
            raise ValidationError('Cần check-in và phân ghế trước khi phục vụ.')
        if Appointment.objects.filter(employee=a.employee, status=Appointment.Status.IN_SERVICE).exclude(pk=a.pk).exists():
            raise ValidationError('Stylist đang phục vụ khách khác. Vui lòng hoàn tất lịch đó trước.')
        from .scheduling import validate_resources
        validate_resources(a.branch,a.employee,a.start_at,a.end_at,a.pk)
        a.service_started_at = now
        a.status = Appointment.Status.IN_SERVICE
        message = 'Bắt đầu phục vụ'
    elif action == 'finish':
        if a.status != Appointment.Status.IN_SERVICE:
            raise ValidationError('Chỉ hoàn tất lịch đang phục vụ.')
        a.service_finished_at = now
        a.status = Appointment.Status.AWAITING_PAYMENT
        message = 'Đã phục vụ xong, chờ thanh toán; đã giải phóng nguồn lực'
    elif action == 'pay':
        if a.status != Appointment.Status.AWAITING_PAYMENT:
            raise ValidationError('Cần hoàn tất phục vụ trước khi thu tiền, mỗi lịch chỉ thu một lần.')
        from .business import ensure_open_day, checkout
        ensure_open_day(a.branch, timezone.localdate())
        payment = PaymentFactory.create(method)
        payment.validate(confirmation)
        checkout(a, actor, payment.method, redeem_points, voucher_code, quoted_total)
        a.status = Appointment.Status.COMPLETED
        message = 'Đã thanh toán và hoàn thành dịch vụ'
    elif action == 'no_show':
        if a.status != Appointment.Status.BOOKED or now < a.start_at + timedelta(minutes=a.branch.late_minutes):
            raise ValidationError('Chỉ đánh dấu không đến sau thời gian chờ khách muộn của chi nhánh.')
        a.status = Appointment.Status.NO_SHOW
        message = 'Khách không đến'
    else:
        raise ValidationError('Thao tác không hợp lệ.')
    a.save(update_fields=['status', 'chair', 'checked_in_at', 'service_started_at', 'service_finished_at', 'end_at'])
    record_change(a, actor, action, reason or message, before)
    emit(a, actor, message)
    return a

