"""Additional first-party screens; all mutable actions require POST and ownership."""

from datetime import date, timedelta
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import (
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
)
from django.core.cache import cache
from django.db.models import Q, Sum
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect
from django.urls import path, reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from .features import page, paginate, ReportFilterForm, report_queryset, download
from .management_views import manager_required
from .models import Notification, AuditLog, Appointment, Employee, Shift, Invoice
from .views import operator_required, appointments_for, branches_for
from .authentication import LockedPasswordResetConfirmView


class ResetView(PasswordResetView):
    template_name = "auth/password_reset.html"
    email_template_name = "auth/password_reset_email.txt"
    subject_template_name = "auth/password_reset_subject.txt"
    success_url = reverse_lazy("password_reset_done")

    def form_valid(self, form):
        # Generic response for existing/unknown addresses and repeated submissions.
        from .hardening import consume

        allowed, _ = consume("reset-mailbox", form.cleaned_data["email"].casefold(), 1, 60)
        if not allowed:
            return redirect(self.success_url)
        return super().form_valid(form)


@login_required
@require_GET
def notifications(request):
    qs = request.user.notifications.select_related("appointment").order_by("-created_at", "-pk")
    state = request.GET.get("state", "")
    if state == "unread":
        qs = qs.filter(read_at__isnull=True)
    if state == "read":
        qs = qs.filter(read_at__isnull=False)
    return page(
        request,
        "Thông báo của tôi",
        "operations/notifications.html",
        {
            "page_obj": paginate(request, qs),
            "unread_count": request.user.notifications.filter(read_at__isnull=True).count(),
        },
    )


@login_required
@require_POST
def read_notification(request, pk=None):
    if pk is None:
        request.user.notifications.filter(read_at__isnull=True).update(read_at=timezone.now())
    else:
        item = get_object_or_404(Notification, pk=pk, recipient=request.user)
        Notification.objects.filter(
            pk=item.pk, recipient=request.user, read_at__isnull=True
        ).update(read_at=timezone.now())
    messages.success(request, "Đã đánh dấu thông báo đã đọc.")
    return redirect("notifications")


@login_required
@require_GET
def points(request):
    qs = request.user.point_entries.select_related("invoice__appointment").all()
    return page(
        request, "Điểm tích lũy", "operations/points.html", {"page_obj": paginate(request, qs)}
    )


class AuditFilterForm(forms.Form):
    q = forms.CharField(label="Nội dung hoặc mã lịch", required=False, max_length=100)
    actor = forms.CharField(label="Tên người thao tác", required=False, max_length=100)
    start = forms.DateField(
        label="Từ ngày", required=False, widget=forms.DateInput(attrs={"type": "date"})
    )
    end = forms.DateField(
        label="Đến ngày", required=False, widget=forms.DateInput(attrs={"type": "date"})
    )

    def clean(self):
        data = super().clean()
        if data.get("start") and data.get("end") and data["start"] > data["end"]:
            self.add_error("end", "Ngày kết thúc phải từ ngày bắt đầu.")
        return data


@manager_required
@require_GET
def audit(request):
    form = AuditFilterForm(request.GET)
    qs = AuditLog.objects.select_related("actor", "appointment").order_by("-created_at", "-pk")
    if form.is_valid():
        data = form.cleaned_data
        if data["actor"]:
            qs = qs.filter(
                Q(actor__username__icontains=data["actor"])
                | Q(actor__full_name__icontains=data["actor"])
            )
        if data["q"]:
            condition = Q(action__icontains=data["q"])
            code = data["q"].upper().removeprefix("LH")
            if code.isascii() and code.isdecimal() and len(code) < 19:
                condition |= Q(appointment_id=int(code))
            qs = qs.filter(condition)
        if data["start"]:
            qs = qs.filter(created_at__date__gte=data["start"])
        if data["end"]:
            qs = qs.filter(created_at__date__lte=data["end"])
    else:
        qs = qs.none()
    return page(
        request,
        "Nhật ký thao tác",
        "operations/audit.html",
        {"form": form, "page_obj": paginate(request, qs), "nav_section": "audit"},
        staff=True,
    )


class WeekFilterForm(forms.Form):
    date = forms.DateField(
        label="Một ngày trong tuần",
        widget=forms.DateInput(attrs={"type": "date", "min": "1900-01-01", "max": "2100-12-31"}),
    )
    branch = forms.ModelChoiceField(
        label="Chi nhánh",
        required=False,
        queryset=Employee.objects.none(),
        empty_label="Mọi chi nhánh được phép",
    )
    employee = forms.ModelChoiceField(
        label="Stylist", required=False, queryset=Employee.objects.none(), empty_label="Mọi stylist"
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["branch"].queryset = branches_for(user)
        self.fields["employee"].queryset = Employee.objects.filter(branch__in=branches_for(user))

    def clean(self):
        data = super().clean()
        if data.get("date") and not 1900 <= data["date"].year <= 2100:
            self.add_error("date", "Chọn năm trong khoảng 1900–2100.")
        if (
            data.get("branch")
            and data.get("employee")
            and data["employee"].branch_id != data["branch"].pk
        ):
            self.add_error("employee", "Stylist không thuộc chi nhánh đã chọn.")
        return data


@operator_required
@require_GET
def week(request):
    data = request.GET.copy()
    if "date" not in data:
        data["date"] = str(timezone.localdate())
    form = WeekFilterForm(data, user=request.user)
    days = []
    if form.is_valid():
        chosen = form.cleaned_data["date"]
        start = chosen - timedelta(days=chosen.weekday())
        end = start + timedelta(days=6)
        appts = appointments_for(request.user).filter(start_at__date__range=(start, end))
        shifts = Shift.objects.filter(
            employee__branch__in=branches_for(request.user), start_at__date__range=(start, end)
        ).select_related("employee__branch")
        branch, employee = form.cleaned_data.get("branch"), form.cleaned_data.get("employee")
        if branch:
            appts = appts.filter(branch=branch)
            shifts = shifts.filter(employee__branch=branch)
        if employee:
            appts = appts.filter(employee=employee)
            shifts = shifts.filter(employee=employee)
        all_appts, all_shifts = (
            list(appts.order_by("start_at", "pk")),
            list(shifts.order_by("start_at", "pk")),
        )
        for offset in range(7):
            day = start + timedelta(days=offset)
            days.append(
                {
                    "date": day,
                    "appointments": [a for a in all_appts if timezone.localdate(a.start_at) == day],
                    "shifts": [s for s in all_shifts if timezone.localdate(s.start_at) == day],
                }
            )
        prev_data, next_data = data.copy(), data.copy()
        prev_data["date"], next_data["date"] = (
            str(start - timedelta(days=7)),
            str(start + timedelta(days=7)),
        )
    else:
        start = end = None
        prev_data = next_data = {}
    return page(
        request,
        "Lịch điều hành theo tuần",
        "operations/week.html",
        {
            "form": form,
            "days": days,
            "start": start,
            "end": end,
            "previous_query": prev_data.urlencode() if days else "",
            "next_query": next_data.urlencode() if days else "",
            "nav_section": "week",
        },
        staff=True,
    )


def performance_data(request):
    form = ReportFilterForm(request.GET, user=request.user)
    form.fields.pop("q")
    invoices, start, end = report_queryset(request, form)
    appts = appointments_for(request.user).filter(start_at__date__range=(start, end))
    branch = form.cleaned_data.get("branch")
    if branch:
        appts = appts.filter(branch=branch)
    total = appts.count()
    cancelled, no_show = (
        appts.filter(status="cancelled").count(),
        appts.filter(status="no_show").count(),
    )
    previous_end = start - timedelta(days=1)
    previous_start = previous_end - (end - start)
    previous = Invoice.objects.filter(
        appointment__in=appointments_for(request.user),
        paid_at__date__range=(previous_start, previous_end),
    )
    if branch:
        previous = previous.filter(appointment__branch=branch)
    from .features import refunds_for_report

    refund_total = sum(r.amount for r in refunds_for_report(request, start, end, form))
    revenue = invoices.aggregate(value=Sum("total"))["value"] or 0
    prior = previous.aggregate(value=Sum("total"))["value"] or 0
    services, stylists = {}, {}
    for invoice in (
        invoices.select_related("appointment__employee")
        .prefetch_related("appointment__items")
        .iterator(chunk_size=200)
    ):
        appointment = invoice.appointment
        row = stylists.setdefault(
            appointment.employee_id, {"name": appointment.employee.name, "count": 0, "total": 0}
        )
        row["count"] += 1
        row["total"] += invoice.total
        items = list(appointment.items.all())
        gross = sum(item.price for item in items)
        allocated = 0
        for index, item in enumerate(items):
            share = (
                invoice.total - allocated
                if index == len(items) - 1
                else invoice.total * item.price // gross
                if gross
                else 0
            )
            allocated += share
            row = services.setdefault(item.service_id, {"name": item.name, "count": 0, "total": 0})
            row["count"] += 1
            row["total"] += share
    return {
        "form": form,
        "start": start,
        "end": end,
        "total_bookings": total,
        "cancelled": cancelled,
        "no_show": no_show,
        "cancel_rate": round(cancelled * 100 / total, 1) if total else 0,
        "no_show_rate": round(no_show * 100 / total, 1) if total else 0,
        "refunds": refund_total,
        "net": revenue - refund_total,
        "revenue": revenue,
        "previous_revenue": prior,
        "difference": revenue - prior,
        "change": round((revenue - prior) * 100 / prior, 1) if prior else None,
        "services": sorted(services.values(), key=lambda r: (-r["count"], r["name"])),
        "stylists": sorted(stylists.values(), key=lambda r: (-r["total"], r["name"])),
        "nav_section": "performance",
    }


@operator_required
@require_GET
def performance(request, fmt=None):
    try:
        context = performance_data(request)
    except ValueError as error:
        if fmt:
            return HttpResponseBadRequest(str(error))
        form = ReportFilterForm(request.GET, user=request.user)
        form.fields.pop("q")
        form.is_valid()
        context = {"form": form, "invalid": True, "nav_section": "performance"}
    if fmt:
        rows = [
            ["Chỉ số", "Lịch hẹn", context["total_bookings"], ""],
            ["Chỉ số", "Lịch hủy", context["cancelled"], ""],
            ["Chỉ số", "Không đến", context["no_show"], ""],
            ["Chỉ số", "Doanh thu kỳ trước", "", context["previous_revenue"]],
            ["Chỉ số", "Thu hóa đơn kỳ này", "", context["revenue"]],
            ["Chỉ số", "Hoàn tiền kỳ này", "", context["refunds"]],
            ["Chỉ số", "Thu ròng kỳ này", "", context["net"]],
        ]
        for group in ("services", "stylists"):
            rows += [
                [
                    "Dịch vụ" if group == "services" else "Stylist",
                    row["name"],
                    row["count"],
                    row["total"],
                ]
                for row in context[group]
            ]
        return download(
            fmt,
            "Hiệu quả hoạt động",
            ["Nhóm", "Nội dung", "Số lượt", "Thực thu (VNĐ)"],
            rows,
            "hieu-qua",
        )
    return page(request, "Hiệu quả hoạt động", "operations/performance.html", context, staff=True)


urlpatterns = [
    path("quen-mat-khau/", ResetView.as_view(), name="password_reset"),
    path(
        "quen-mat-khau/da-gui/",
        PasswordResetDoneView.as_view(template_name="auth/password_reset_done.html"),
        name="password_reset_done",
    ),
    path(
        "dat-lai-mat-khau/<uidb64>/<token>/",
        LockedPasswordResetConfirmView.as_view(
            template_name="auth/password_reset_confirm.html",
            success_url=reverse_lazy("password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "dat-lai-mat-khau/hoan-tat/",
        PasswordResetCompleteView.as_view(template_name="auth/password_reset_complete.html"),
        name="password_reset_complete",
    ),
    path("thong-bao/", notifications, name="notifications"),
    path("thong-bao/doc-tat-ca/", read_notification, name="notifications_read_all"),
    path("thong-bao/<int:pk>/da-doc/", read_notification, name="notification_read"),
    path("diem-tich-luy/", points, name="points"),
    path("quan-ly/nhat-ky/", audit, name="audit"),
    path("quan-ly/lich-tuan/", week, name="week"),
    path("quan-ly/hieu-qua/", performance, name="performance"),
    path("quan-ly/hieu-qua/xuat/<str:fmt>/", performance, name="performance_export"),
]
