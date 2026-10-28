"""Branch operations. Mutations share branch locks with booking/checkout."""

from datetime import timedelta
from uuid import uuid4
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction, connection
from django.db.models import Sum
from django.utils import timezone
from .models import (
    Branch,
    User,
    Employee,
    Appointment,
    AppointmentItem,
    AppointmentChange,
    Invoice,
    PointEntry,
    Voucher,
    VoucherUse,
    Commission,
    Refund,
    DailyClosing,
    EmployeeAbsence,
    BranchClosure,
    Product,
    Stock,
    StockMovement,
    EmailOutbox,
    ACTIVE_STATUSES,
)
from .services import assert_operator, book, emit, validate_slot


def branch_lock(actor, branch_id, manage=False):
    branch = Branch.objects.select_for_update().get(pk=branch_id)
    current = assert_operator(actor, branch_id)
    if manage and not current.can_manage_branch:
        raise PermissionDenied
    return branch


def snapshot(a):
    return {
        "status": a.status,
        "branch": a.branch_id,
        "employee": a.employee_id,
        "chair": a.chair_id,
        "start": a.start_at.isoformat(),
        "end": a.end_at.isoformat(),
        "checked_in": a.checked_in_at.isoformat() if a.checked_in_at else None,
        "started": a.service_started_at.isoformat() if a.service_started_at else None,
        "finished": a.service_finished_at.isoformat() if a.service_finished_at else None,
        "items": list(a.items.values("service_id", "name", "price", "duration")),
    }


def record_change(a, actor, action, reason, before):
    AppointmentChange.objects.create(
        appointment=a,
        actor=actor,
        action=action,
        reason=reason[:250],
        before=before,
        after=snapshot(a),
    )


def ensure_open_day(branch, day):
    if DailyClosing.objects.filter(branch=branch, day=day).exists():
        raise ValidationError("Ngày này đã chốt sổ. Giao dịch mới cần thực hiện ở ngày đang mở.")


def payment_quote(a, customer, redeem_points=0, voucher_code="", lock=False):
    if isinstance(redeem_points, bool) or not isinstance(redeem_points, int) or redeem_points < 0:
        raise ValidationError("Số điểm phải là số nguyên không âm.")
    if redeem_points and customer.points_debt:
        raise ValidationError("Khách còn điểm cần thu hồi sau hoàn tiền; chưa thể đổi điểm.")
    if redeem_points > customer.points or redeem_points * 1000 > a.total // 5:
        raise ValidationError("Điểm không đủ hoặc giảm quá 20% giá dịch vụ.")
    voucher = None
    voucher_discount = 0
    if voucher_code.strip():
        if redeem_points:
            raise ValidationError("Chọn giảm từ điểm hoặc voucher, không cộng dồn.")
        qs = Voucher.objects.select_for_update() if lock else Voucher.objects.all()
        voucher = qs.filter(code__iexact=voucher_code.strip()).first()
        now = timezone.now()
        if (
            not voucher
            or not voucher.active
            or not voucher.starts_at <= now <= voucher.ends_at
            or voucher.branch_id not in (None, a.branch_id)
            or a.total < voucher.min_total
        ):
            raise ValidationError(
                "Voucher không hợp lệ, khác chi nhánh, hết hạn hoặc chưa đủ giá trị đơn."
            )
        if (
            voucher.uses.count() >= voucher.max_uses
            or voucher.uses.filter(customer=customer).exists()
        ):
            raise ValidationError("Voucher hết lượt hoặc khách đã sử dụng.")
        voucher_discount = min(voucher.amount, a.total)
    return a.total - redeem_points * 1000 - voucher_discount, voucher_discount, voucher


def checkout(a, actor, method, redeem_points=0, voucher_code="", quoted_total=None):
    customer = User.objects.select_for_update().get(pk=a.customer_id)
    total, voucher_discount, voucher = payment_quote(
        a, customer, redeem_points, voucher_code, lock=True
    )
    if quoted_total is not None and quoted_total != total:
        raise ValidationError("Số tiền đã thay đổi. Xem lại số cần thu trước khi xác nhận.")
    invoice = Invoice.objects.create(
        appointment=a,
        total=a.total - redeem_points * 1000 - voucher_discount,
        discount=redeem_points * 1000,
        points_used=redeem_points,
        method=method,
        cashier=actor,
        voucher_discount=voucher_discount,
        voucher_code=voucher.code if voucher else "",
    )
    if voucher:
        VoucherUse.objects.create(voucher=voucher, invoice=invoice, customer=customer)
    balance = customer.points
    if not customer.point_entries.exists() and balance:
        PointEntry.objects.create(
            customer=customer, kind="opening", amount=balance, balance=balance
        )
    if redeem_points:
        balance -= redeem_points
        PointEntry.objects.create(
            customer=customer,
            invoice=invoice,
            kind="redeemed",
            amount=-redeem_points,
            balance=balance,
        )
    gross_earned = invoice.total // 10000
    debt_paid = min(customer.points_debt, gross_earned)
    earned = gross_earned - debt_paid
    customer.points_debt -= debt_paid
    invoice.points_earned = earned
    invoice.points_debt_paid = debt_paid
    invoice.save(update_fields=["points_earned", "points_debt_paid"])
    balance += earned
    PointEntry.objects.create(
        customer=customer, invoice=invoice, kind="earned", amount=earned, balance=balance
    )
    customer.points = balance
    customer.save(update_fields=["points", "points_debt"])
    rate = a.employee.commission_percent
    Commission.objects.create(
        invoice=invoice, employee=a.employee, percent=rate, amount=invoice.total * rate // 100
    )
    return invoice


@transaction.atomic
def walk_in(
    *,
    actor,
    branch_id,
    employee_id,
    service_ids,
    start,
    name="",
    phone="",
    email="",
    customer_id=None,
):
    branch_lock(actor, branch_id)
    actor = assert_operator(actor, branch_id)
    if customer_id:
        customer = User.objects.get(pk=customer_id, role="customer", is_active=True)
        if not actor.is_manager and not customer.appointments.filter(branch_id=branch_id).exists():
            raise ValidationError(
                "Chọn khách đã có hồ sơ tại chi nhánh hoặc nhập thông tin khách mới."
            )
    else:
        from .models import phone_validator

        phone_validator(phone)
        if not name.strip():
            raise ValidationError("Nhập tên khách hàng.")
        # Same phone serializes across branches without exposing another branch's customer data.
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", ["walkin:" + phone])
        existing = User.objects.filter(phone=phone, role="customer", is_active=True)
        if existing.exists():
            if existing.count() != 1:
                raise ValidationError(
                    "Điện thoại có nhiều hồ sơ. Chọn đúng khách trong danh sách hoặc liên hệ quản trị."
                )
            customer = existing.first()
            if customer.full_name.casefold().strip() != name.casefold().strip():
                raise ValidationError(
                    "Điện thoại đã có hồ sơ. Kiểm tra lại tên khách, không tự tạo hồ sơ trùng."
                )
        else:
            customer = User(
                username="quay_" + uuid4().hex,
                full_name=name.strip(),
                phone=phone,
                email=email,
                role="customer",
            )
            customer.set_unusable_password()
            customer.save()
    a = book(
        customer=customer,
        actor=actor,
        branch_id=branch_id,
        employee_id=employee_id,
        service_ids=service_ids,
        start=start,
        source="walkin",
    )
    record_change(a, actor, "walkin", "Tiếp nhận khách tại quầy", {})
    return a


@transaction.atomic
def change_services(*, actor, pk, service_ids, reason):
    original = Appointment.objects.get(pk=pk)
    branch_lock(actor, original.branch_id)
    a = Appointment.objects.select_for_update().get(pk=pk)
    if a.status not in ACTIVE_STATUSES:
        raise ValidationError("Chỉ sửa dịch vụ trước khi hoàn tất phục vụ.")
    if not reason.strip():
        raise ValidationError("Nhập lý do và xác nhận khách đồng ý thay đổi dịch vụ.")
    from .models import Service

    selected = list(Service.objects.filter(pk__in=set(service_ids), active=True).order_by("pk"))
    if not selected or len(selected) != len(set(service_ids)):
        raise ValidationError("Chọn dịch vụ đang hoạt động.")
    old = {i.service_id: i for i in a.items.all()}
    before = snapshot(a)
    # Unchanged lines keep their original price/duration snapshots.
    duration = sum(old[s.pk].duration if s.pk in old else s.duration for s in selected)
    if duration > 480:
        raise ValidationError("Tổng thời lượng tối đa 8 giờ.")
    end = validate_slot(
        a.branch, a.employee, a.start_at, duration, exclude_id=a.pk, allow_past=True
    )
    if (
        Appointment.objects.filter(
            customer=a.customer, status__in=ACTIVE_STATUSES, start_at__lt=end, end_at__gt=a.start_at
        )
        .exclude(pk=a.pk)
        .exists()
    ):
        raise ValidationError("Thời lượng mới trùng lịch khác của khách.")
    a.items.exclude(service_id__in=service_ids).delete()
    for s in selected:
        if s.pk not in old:
            AppointmentItem.objects.create(
                appointment=a, service=s, name=s.name, price=s.price, duration=s.duration
            )
    a.end_at = end
    a.save(update_fields=["end_at"])
    record_change(a, actor, "services", reason, before)
    emit(a, actor, "Đã cập nhật dịch vụ sau khi khách xác nhận")
    return a


@transaction.atomic
def extend_service(*, actor, pk, minutes, reason):
    original = Appointment.objects.get(pk=pk)
    branch_lock(actor, original.branch_id)
    a = Appointment.objects.select_for_update().get(pk=pk)
    if a.status != "in_service" or minutes not in (15, 30, 45, 60) or not reason.strip():
        raise ValidationError("Chỉ gia hạn lịch đang phục vụ, 15–60 phút, bắt buộc lý do.")
    before = snapshot(a)
    duration = int((a.end_at - a.start_at).total_seconds() // 60) + minutes
    if duration > 480:
        raise ValidationError("Tổng thời gian tối đa 8 giờ.")
    end = validate_slot(
        a.branch, a.employee, a.start_at, duration, exclude_id=a.pk, allow_past=True
    )
    if (
        Appointment.objects.filter(
            customer=a.customer, status__in=ACTIVE_STATUSES, start_at__lt=end, end_at__gt=a.start_at
        )
        .exclude(pk=a.pk)
        .exists()
    ):
        raise ValidationError("Gia hạn trùng lịch khác của khách. Hãy điều phối trước.")
    a.end_at = end
    a.save(update_fields=["end_at"])
    record_change(a, actor, "extend", reason, before)
    emit(a, actor, "Đã gia hạn thời gian phục vụ")
    return a


@transaction.atomic
def register_interruption(*, actor, branch_id, start, end, reason, employee_id=None):
    branch = branch_lock(actor, branch_id, manage=True)
    if end <= start or not reason.strip():
        raise ValidationError("Khoảng nghỉ và lý do không hợp lệ.")
    if employee_id:
        employee = Employee.objects.get(pk=employee_id, branch=branch)
        item = EmployeeAbsence.objects.create(
            employee=employee, start_at=start, end_at=end, reason=reason, actor=actor
        )
        affected = Appointment.objects.filter(
            employee=employee, status__in=ACTIVE_STATUSES, start_at__lt=end, end_at__gt=start
        )
    else:
        item = BranchClosure.objects.create(
            branch=branch, start_at=start, end_at=end, reason=reason
        )
        affected = Appointment.objects.filter(
            branch=branch, status__in=ACTIVE_STATUSES, start_at__lt=end, end_at__gt=start
        )
    for a in affected:
        record_change(a, actor, "interruption", reason, snapshot(a))
        emit(a, actor, "Lịch bị ảnh hưởng do tạm nghỉ; chi nhánh sẽ liên hệ điều phối")
        EmailOutbox.objects.filter(
            appointment=a, key__startswith="reminder:", sent_at__isnull=True
        ).update(cancelled=True)
    from .models import AuditLog

    AuditLog.objects.create(
        actor=actor, branch=branch, action=f"Tạo lịch nghỉ #{item.pk}: {reason}"[:100]
    )
    return item


@transaction.atomic
def refund_invoice(*, actor, invoice_id, reason):
    original = Invoice.objects.select_related("appointment").get(pk=invoice_id)
    branch = branch_lock(actor, original.appointment.branch_id, manage=True)
    ensure_open_day(branch, timezone.localdate())
    inv = Invoice.objects.select_for_update().get(pk=invoice_id)
    if not reason.strip():
        raise ValidationError("Bắt buộc lý do hoàn tiền.")
    if Refund.objects.filter(invoice=inv).exists():
        raise ValidationError("Hóa đơn đã được hoàn tiền.")
    customer = User.objects.select_for_update().get(pk=original.appointment.customer_id)
    # Refund money even when earned points have already been spent. Track the
    # outstanding points separately and offset future earnings, never a negative balance.
    recoverable = min(customer.points, inv.points_earned)
    debt = inv.points_earned - recoverable + inv.points_debt_paid
    balance = customer.points - recoverable + inv.points_used
    # Restored redeemed points repay outstanding recovery before becoming
    # spendable again. This preserves entitlement in either refund order.
    customer.points_debt += debt
    repaid = min(balance, customer.points_debt)
    balance -= repaid
    customer.points_debt -= repaid
    delta = balance - customer.points
    refund = Refund.objects.create(
        invoice=inv,
        amount=inv.total,
        reason=reason,
        actor=actor,
        points_debt_added=debt,
        points_debt_repaid=repaid,
    )
    PointEntry.objects.create(
        customer=customer, invoice=inv, kind="refund", amount=delta, balance=balance
    )
    customer.points = balance
    customer.save(update_fields=["points", "points_debt"])
    a = original.appointment
    record_change(a, actor, "refund", reason, snapshot(a))
    emit(a, actor, "Đã ghi nhận hoàn toàn bộ số tiền của hóa đơn")
    return refund


def cash_totals(branch, day):
    invoices = Invoice.objects.filter(appointment__branch=branch, paid_at__date=day)
    receipts = invoices.filter(method="cash").aggregate(n=Sum("total"))["n"] or 0
    refunds = (
        Refund.objects.filter(
            invoice__appointment__branch=branch, invoice__method="cash", created_at__date=day
        ).aggregate(n=Sum("amount"))["n"]
        or 0
    )
    return receipts - refunds, invoices.count()


@transaction.atomic
def close_day(*, actor, branch_id, day, counted, reason):
    branch = branch_lock(actor, branch_id, manage=True)
    if day > timezone.localdate() or counted < 0:
        raise ValidationError("Chỉ chốt ngày hôm nay hoặc trước đó; tiền thực đếm không âm.")
    ensure_open_day(branch, day)
    if Appointment.objects.filter(
        branch=branch,
        status__in=["checked_in", "in_service", "awaiting_payment"],
        start_at__date__lte=day,
    ).exists():
        raise ValidationError(
            "Còn khách đang chờ, phục vụ hoặc chờ thanh toán. Xử lý các lịch này trước khi chốt."
        )
    expected, count = cash_totals(branch, day)
    if counted != expected and not reason.strip():
        raise ValidationError("Có chênh lệch tiền mặt, bắt buộc ghi lý do.")
    return DailyClosing.objects.create(
        branch=branch,
        day=day,
        expected_cash=expected,
        counted_cash=counted,
        invoices_count=count,
        reason=reason,
        actor=actor,
    )


@transaction.atomic
def move_stock(*, actor, branch_id, product_id, amount, kind, reason, target_id=None):
    assert_operator(actor, branch_id)
    if not actor.can_manage_branch:
        raise PermissionDenied
    if kind == "transfer" and not actor.is_manager:
        raise PermissionDenied
    ids = sorted(set([branch_id] + ([target_id] if target_id else [])))
    list(Branch.objects.select_for_update().filter(pk__in=ids).order_by("pk"))
    current = assert_operator(actor, branch_id)
    if not current.can_manage_branch or (kind == "transfer" and not current.is_manager):
        raise PermissionDenied
    if not Product.objects.filter(pk=product_id, active=True).exists():
        raise ValidationError("Sản phẩm không hoạt động.")
    if (
        kind not in ("receipt", "consume", "adjust", "transfer")
        or not reason.strip()
        or not isinstance(amount, int)
        or amount == 0
    ):
        raise ValidationError("Kiểm tra loại giao dịch, số lượng và lý do.")
    if kind in ("receipt", "consume", "transfer") and amount < 0:
        raise ValidationError("Nhập số lượng lớn hơn 0.")
    if kind == "transfer" and (
        target_id == branch_id or not Branch.objects.filter(pk=target_id, active=True).exists()
    ):
        raise ValidationError("Chọn chi nhánh nhận khác chi nhánh xuất, đang hoạt động.")
    stock, _ = Stock.objects.get_or_create(branch_id=branch_id, product_id=product_id)
    delta = -amount if kind in ("consume", "transfer") else amount
    if stock.quantity + delta < 0:
        raise ValidationError("Không đủ tồn kho; không được xuất âm.")
    reference = "KHO" + uuid4().hex[:12].upper()
    stock.quantity += delta
    stock.save(update_fields=["quantity"])
    StockMovement.objects.create(
        stock=stock,
        amount=delta,
        balance=stock.quantity,
        kind=kind,
        reason=reason,
        actor=actor,
        reference=reference,
    )
    if kind == "transfer":
        target, _ = Stock.objects.get_or_create(branch_id=target_id, product_id=product_id)
        target.quantity += amount
        target.save(update_fields=["quantity"])
        StockMovement.objects.create(
            stock=target,
            amount=amount,
            balance=target.quantity,
            kind=kind,
            reason=reason,
            actor=actor,
            reference=reference,
        )
    return stock
