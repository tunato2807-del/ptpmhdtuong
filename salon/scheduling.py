"""Branch capacity uses a sweep of half-open intervals, not total overlap count."""

from datetime import timedelta
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import (
    Appointment,
    Chair,
    EmployeeAbsence,
    BranchClosure,
    DailyClosing,
    ACTIVE_STATUSES,
)


def validate_resources(branch, employee, start, end, exclude_id=None):
    if EmployeeAbsence.objects.filter(
        employee=employee, active=True, start_at__lt=end, end_at__gt=start
    ).exists():
        raise ValidationError(
            "Stylist có lịch nghỉ trong khoảng thời gian này. Chọn stylist hoặc giờ khác."
        )
    if BranchClosure.objects.filter(
        branch=branch, active=True, start_at__lt=end, end_at__gt=start
    ).exists():
        raise ValidationError("Chi nhánh tạm nghỉ trong khoảng thời gian đã chọn.")
    if DailyClosing.objects.filter(branch=branch, day=timezone.localdate(start)).exists():
        raise ValidationError("Ngày đã chốt sổ, không nhận thêm lịch phục vụ.")
    capacity = Chair.objects.filter(branch=branch, active=True).count()
    if capacity == 0:
        raise ValidationError("Chi nhánh chưa có ghế sẵn sàng.")
    events = [(start, 1), (end, -1)]
    qs = Appointment.objects.filter(
        branch=branch, status__in=ACTIVE_STATUSES, start_at__lt=end, end_at__gt=start
    ).exclude(pk=exclude_id)
    for a, b in qs.values_list("start_at", "end_at"):
        events.extend([(max(a, start), 1), (min(b, end), -1)])
    count = 0
    for _, delta in sorted(events, key=lambda item: (item[0], item[1])):
        count += delta
        if count > capacity:
            raise ValidationError("Chi nhánh đã hết sức chứa ghế trong khung giờ này.")


def peak_existing_capacity(branch):
    events = []
    for start, end in Appointment.objects.filter(
        branch=branch, status__in=ACTIVE_STATUSES
    ).values_list("start_at", "end_at"):
        events.extend([(start, 1), (end, -1)])
    count = peak = 0
    for _, delta in sorted(events, key=lambda v: (v[0], v[1])):
        count += delta
        peak = max(peak, count)
    return peak


def day_slots(branch, employee, day, duration, exclude_id=None):
    """Batch-read a day's resources; the write path still validates under locks."""
    from .models import Shift
    from .services import local_at

    now = timezone.now()
    today = timezone.localdate(now)
    if (
        not 15 <= duration <= 480
        or not branch.active
        or not employee.active
        or employee.branch_id != branch.pk
        or not today <= day <= today + timedelta(days=branch.booking_days)
    ):
        return []
    opening = local_at(day, branch.opens_at)
    closing = local_at(day, branch.closes_at)
    if DailyClosing.objects.filter(branch=branch, day=day).exists():
        return []
    capacity = Chair.objects.filter(branch=branch, active=True).count()
    if not capacity:
        return []
    shifts = list(
        Shift.objects.filter(
            employee=employee, start_at__lt=closing, end_at__gt=opening
        ).values_list("start_at", "end_at")
    )
    blocked = list(
        EmployeeAbsence.objects.filter(
            employee=employee, active=True, start_at__lt=closing, end_at__gt=opening
        ).values_list("start_at", "end_at")
    )
    blocked += list(
        BranchClosure.objects.filter(
            branch=branch, active=True, start_at__lt=closing, end_at__gt=opening
        ).values_list("start_at", "end_at")
    )
    reserved = list(
        Appointment.objects.filter(
            branch=branch, status__in=ACTIVE_STATUSES, start_at__lt=closing, end_at__gt=opening
        )
        .exclude(pk=exclude_id)
        .values_list("employee_id", "start_at", "end_at")
    )
    cursor = opening.replace(second=0, microsecond=0)
    if opening.second or opening.microsecond:
        cursor += timedelta(minutes=1)
    if cursor.minute % 15:
        cursor += timedelta(minutes=15 - cursor.minute % 15)
    result = []
    while cursor + timedelta(minutes=duration) <= closing:
        end = cursor + timedelta(minutes=duration)
        fits = (
            cursor >= now
            and any(a <= cursor and b >= end for a, b in shifts)
            and not any(a < end and b > cursor for a, b in blocked)
            and not any(emp == employee.pk and a < end and b > cursor for emp, a, b in reserved)
        )
        if fits:
            events = [(cursor, 1), (end, -1)]
            for _, a, b in reserved:
                if a < end and b > cursor:
                    events.extend([(max(a, cursor), 1), (min(b, end), -1)])
            used = 0
            for _, delta in sorted(events, key=lambda v: (v[0], v[1])):
                used += delta
                if used > capacity:
                    fits = False
                    break
        if fits:
            result.append(cursor.strftime("%H:%M"))
        cursor += timedelta(minutes=15)
    return result
