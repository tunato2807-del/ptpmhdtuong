"""Multi-branch application screens. Every queryset and POST is scoped independently."""

from datetime import timedelta
from functools import wraps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction, IntegrityError
from django.db.models import Q, Sum, Count, F
from django.db.models.deletion import ProtectedError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import path
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from .models import (
    Branch,
    Employee,
    User,
    Chair,
    Shift,
    Appointment,
    AppointmentChange,
    Invoice,
    Refund,
    Voucher,
    Product,
    Stock,
    StockMovement,
    Commission,
    DailyClosing,
    EmployeeAbsence,
    BranchClosure,
    EmailOutbox,
    AuditLog,
    ACTIVE_STATUSES,
)
from .views import operator_required, branches_for, appointments_for, chosen_day
from .features import page, paginate, download
from .forms import ChairForm, ShiftForm, ConfirmDeleteForm
from .business_forms import (
    WalkInForm,
    ServicesForm,
    ExtendForm,
    InterruptionForm,
    RefundForm,
    ClosingForm,
    StockForm,
    PolicyForm,
    StylistForm,
    BranchAccountForm,
    ProductForm,
    VoucherForm,
    CustomerContactForm,
)
from . import business


def branch_manager_required(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.can_manage_branch:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapped


def scoped_branches(request):
    qs = branches_for(request.user)
    selected = request.GET.get("branch", "")
    if selected.isascii() and selected.isdecimal() and len(selected) < 19:
        return qs.filter(pk=int(selected))
    return qs


def workspace(request, title, context):
    return page(
        request, title, "business/workspace.html", dict(context, nav_section="business"), staff=True
    )


def form_page(request, title, form, hint="", context=None, staff=True):
    return page(
        request,
        title,
        "business/form.html",
        dict(context or {}, form=form, hint=hint, nav_section="business"),
        staff=staff,
    )


@operator_required
@require_GET
def board(request):
    scope = list(scoped_branches(request))
    day = chosen_day(request)

    def grouped(qs, field, **metrics):
        return {r[field]: r for r in qs.values(field).annotate(**metrics).order_by()}

    appointments = grouped(
        Appointment.objects.filter(branch__in=scope, start_at__date=day),
        "branch_id",
        bookings=Count("pk"),
        busy=Count("pk", filter=Q(status__in=["checked_in", "in_service"])),
        waiting=Count("pk", filter=Q(status="awaiting_payment")),
        completed=Count("pk", filter=Q(status="completed")),
    )
    receipts = grouped(
        Invoice.objects.filter(appointment__branch__in=scope, paid_at__date=day),
        "appointment__branch_id",
        total=Sum("total"),
    )
    refunds = grouped(
        Refund.objects.filter(invoice__appointment__branch__in=scope, created_at__date=day),
        "invoice__appointment__branch_id",
        total=Sum("amount"),
    )
    chairs = grouped(
        Chair.objects.filter(branch__in=scope, active=True), "branch_id", total=Count("pk")
    )
    stock = grouped(
        Stock.objects.filter(
            branch__in=scope, quantity__lte=F("product__reorder_level"), product__active=True
        ),
        "branch_id",
        total=Count("pk"),
    )
    closed = set(
        DailyClosing.objects.filter(branch__in=scope, day=day).values_list("branch_id", flat=True)
    )
    rows = []
    for branch in scope:
        income = receipts.get(branch.pk, {}).get("total", 0)
        returned = refunds.get(branch.pk, {}).get("total", 0)
        counts = appointments.get(branch.pk, {})
        rows.append(
            {
                "branch": branch,
                "chairs": chairs.get(branch.pk, {}).get("total", 0),
                "busy": counts.get("busy", 0),
                "bookings": counts.get("bookings", 0),
                "waiting": counts.get("waiting", 0),
                "completed": counts.get("completed", 0),
                "receipts": income,
                "refunds": returned,
                "net": income - returned,
                "closed": branch.pk in closed,
                "stock_low": stock.get(branch.pk, {}).get("total", 0),
            }
        )
    if request.GET.get("export") in ("xlsx", "pdf"):
        data = [
            [r["branch"].name, r["bookings"], r["waiting"], r["receipts"], r["refunds"], r["net"]]
            for r in rows
        ]
        return download(
            request.GET["export"],
            "Đối soát chi nhánh " + str(day),
            ["Chi nhánh", "Lịch hẹn", "Chờ thu", "Thu hóa đơn", "Hoàn tiền", "Thu ròng"],
            data,
            "doi-soat-chi-nhanh",
        )
    appts = (
        appointments_for(request.user)
        .filter(branch__in=scope, start_at__date=day)
        .order_by("start_at", "pk")
    )
    query = request.GET.get("q", "").strip()[:100]
    if query:
        appts = appts.filter(
            Q(customer__full_name__icontains=query) | Q(customer__phone__icontains=query)
        )
    state = request.GET.get("state", "")
    if state in Appointment.Status.values:
        appts = appts.filter(status=state)
    page_obj = paginate(request, appts)
    # Group only the authorized, filtered page. No per-branch queries or hidden extra rows.
    lanes = {row["branch"].pk: row for row in rows}
    for row in rows:
        row["appointments"] = []
    for appointment in page_obj:
        lanes[appointment.branch_id]["appointments"].append(appointment)
    totals = {
        key: sum(row[key] for row in rows)
        for key in ("bookings", "completed", "waiting", "net", "stock_low", "receipts", "refunds")
    }
    return workspace(
        request,
        "Điều hành nhiều chi nhánh",
        {
            "mode": "board",
            "branches": branches_for(request.user),
            "branch_rows": rows,
            "board_totals": totals,
            "day": day,
            "q": query,
            "state": state,
            "states": Appointment.Status.choices,
            "page_obj": page_obj,
        },
    )


@operator_required
@require_http_methods(["GET", "POST"])
def walkin(request):
    now = timezone.localtime()
    rounded = now.replace(second=0, microsecond=0) + timedelta(minutes=15 - now.minute % 15)
    form = WalkInForm(
        request.POST or None,
        user=request.user,
        initial={"start": rounded, "branch": request.user.branch_id},
    )
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            a = business.walk_in(
                actor=request.user,
                branch_id=d["branch"].pk,
                employee_id=d["employee"].pk,
                service_ids=[s.pk for s in d["services"]],
                start=d["start"],
                name=d["name"],
                phone=d["phone"],
                email=d["email"],
                customer_id=d["customer"].pk if d["customer"] else None,
            )
            messages.success(
                request, f"Đã tiếp nhận {a.code}. Kiểm tra giờ đến và check-in để phân ghế."
            )
            return redirect("appointment_detail", pk=a.pk)
        except (ValidationError, IntegrityError, User.DoesNotExist) as e:
            form.add_error(
                None,
                e
                if isinstance(e, ValidationError)
                else "Hồ sơ hoặc khung giờ vừa thay đổi. Kiểm tra lại.",
            )
    return form_page(
        request,
        "Tiếp nhận khách tại quầy",
        form,
        "Khách mới chỉ cần hồ sơ tên, điện thoại; tài khoản tạo tại quầy chưa có mật khẩu đăng nhập. Email là tùy chọn để nhận nhắc lịch.",
    )


@operator_required
@require_http_methods(["GET", "POST"])
def adjust(request, pk, kind):
    a = get_object_or_404(appointments_for(request.user), pk=pk)
    if kind not in ("dich-vu", "gia-han"):
        raise Http404
    cls = ServicesForm if kind == "dich-vu" else ExtendForm
    form = cls(
        request.POST or None,
        initial={"services": list(a.items.values_list("service_id", flat=True))},
    )
    if request.method == "POST" and form.is_valid():
        try:
            if kind == "dich-vu":
                business.change_services(
                    actor=request.user,
                    pk=pk,
                    service_ids=[s.pk for s in form.cleaned_data["services"]],
                    reason=form.cleaned_data["reason"],
                )
            else:
                business.extend_service(
                    actor=request.user,
                    pk=pk,
                    minutes=form.cleaned_data["minutes"],
                    reason=form.cleaned_data["reason"],
                )
            messages.success(request, "Đã cập nhật và ghi lịch sử.")
            return redirect("appointment_detail", pk=pk)
        except (ValidationError, IntegrityError) as e:
            form.add_error(
                None, e if isinstance(e, ValidationError) else "Lịch vừa thay đổi, hãy tải lại."
            )
    return form_page(
        request,
        "Điều chỉnh " + a.code,
        form,
        "Dịch vụ đang giữ nguyên giữ giá đã đặt; dịch vụ mới dùng giá hiện tại. Thời lượng mới phải còn đủ ca, ghế và không đẩy vào lịch khách tiếp theo.",
        {"appointment": a},
    )


@branch_manager_required
@require_http_methods(["GET", "POST"])
def interruptions(request):
    form = InterruptionForm(
        request.POST or None, user=request.user, initial={"branch": request.user.branch_id}
    )
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            business.register_interruption(
                actor=request.user,
                branch_id=d["branch"].pk,
                employee_id=d["employee"].pk if d["employee"] else None,
                start=d["start"],
                end=d["end"],
                reason=d["reason"],
            )
            messages.success(
                request,
                "Đã chặn nhận lịch mới; các lịch bị ảnh hưởng cần được liên hệ và điều phối.",
            )
            return redirect("business_interruptions")
        except (ValidationError, IntegrityError) as e:
            form.add_error(
                None, e if isinstance(e, ValidationError) else "Khoảng nghỉ không hợp lệ."
            )
    scope = branches_for(request.user)
    absences = (
        EmployeeAbsence.objects.filter(employee__branch__in=scope)
        .select_related("employee__branch")
        .order_by("-pk")
    )
    closures = (
        BranchClosure.objects.filter(branch__in=scope).select_related("branch").order_by("-pk")
    )
    impacted = Q(pk__in=[])
    for item in absences.filter(active=True):
        impacted |= Q(
            employee_id=item.employee_id, start_at__lt=item.end_at, end_at__gt=item.start_at
        )
    for item in closures.filter(active=True):
        impacted |= Q(branch_id=item.branch_id, start_at__lt=item.end_at, end_at__gt=item.start_at)
    affected = (
        appointments_for(request.user)
        .filter(impacted, status__in=ACTIVE_STATUSES)
        .distinct()
        .order_by("start_at")
    )
    return workspace(
        request,
        "Lịch nghỉ & điều phối",
        {
            "mode": "interruptions",
            "form": form,
            "absences": absences[:100],
            "closures": closures[:100],
            "page_obj": paginate(request, affected),
        },
    )


@branch_manager_required
@require_POST
def toggle_interruption(request, kind, pk):
    model = EmployeeAbsence if kind == "stylist" else BranchClosure if kind == "chi-nhanh" else None
    if model is None:
        raise Http404
    qs = model.objects.filter(
        **(
            {"employee__branch__in": branches_for(request.user)}
            if kind == "stylist"
            else {"branch__in": branches_for(request.user)}
        )
    )
    item = get_object_or_404(qs, pk=pk)
    with transaction.atomic():
        branch_id = item.employee.branch_id if kind == "stylist" else item.branch_id
        business.branch_lock(request.user, branch_id, manage=True)
        item = model.objects.select_for_update().get(pk=pk)
        # Cancellation only: recreating an interruption must preview/re-notify affected appointments.
        item.active = False
        item.save(update_fields=["active"])
        AuditLog.objects.create(
            actor=request.user, branch_id=branch_id, action=f"Ngừng lịch nghỉ {kind} #{pk}"
        )
    messages.success(request, "Đã ngừng lịch nghỉ; ca làm gốc vẫn được áp dụng.")
    return redirect("business_interruptions")


@branch_manager_required
@require_http_methods(["GET", "POST"])
def refund(request, pk):
    inv = get_object_or_404(
        Invoice.objects.filter(appointment__in=appointments_for(request.user)), pk=pk
    )
    form = RefundForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            business.refund_invoice(
                actor=request.user, invoice_id=pk, reason=form.cleaned_data["reason"]
            )
            messages.success(
                request, "Đã ghi nhận hoàn tiền, điều chỉnh điểm và loại hoa hồng tương ứng."
            )
            return redirect("appointment_detail", pk=inv.appointment_id)
        except (ValidationError, IntegrityError) as e:
            form.add_error(
                None, e if isinstance(e, ValidationError) else "Giao dịch đã được xử lý."
            )
    return form_page(
        request,
        "Hoàn tiền " + inv.code,
        form,
        "Hoàn toàn bộ số thực thu, giữ nguyên hóa đơn gốc. Voucher đã dùng không được hoàn lượt.",
        {"invoice": inv},
    )


@branch_manager_required
@require_http_methods(["GET", "POST"])
def closing(request):
    form = ClosingForm(
        request.POST or None,
        user=request.user,
        initial={"day": timezone.localdate(), "branch": request.user.branch_id},
    )
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            business.close_day(
                actor=request.user,
                branch_id=d["branch"].pk,
                day=d["day"],
                counted=d["counted"],
                reason=d["reason"],
            )
            messages.success(request, "Đã chốt sổ ngày tại chi nhánh.")
            return redirect("business_closing")
        except (ValidationError, IntegrityError) as e:
            form.add_error(None, e if isinstance(e, ValidationError) else "Ngày này đã được chốt.")
    qs = (
        DailyClosing.objects.filter(branch__in=scoped_branches(request))
        .select_related("branch", "actor")
        .order_by("-day", "branch_id")
    )
    preview = [
        {"branch": b, "cash": business.cash_totals(b, timezone.localdate())[0]}
        for b in scoped_branches(request)
    ]
    return workspace(
        request,
        "Đối soát & chốt sổ ngày",
        {"mode": "closing", "form": form, "preview": preview, "page_obj": paginate(request, qs)},
    )


@branch_manager_required
@require_http_methods(["GET", "POST"])
def stock(request):
    form = StockForm(
        request.POST or None, user=request.user, initial={"branch": request.user.branch_id}
    )
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            business.move_stock(
                actor=request.user,
                branch_id=d["branch"].pk,
                product_id=d["product"].pk,
                amount=d["amount"],
                kind=d["kind"],
                reason=d["reason"],
                target_id=d["target"].pk if d.get("target") else None,
            )
            messages.success(request, "Đã ghi giao dịch kho.")
            return redirect("business_stock")
        except (ValidationError, IntegrityError) as e:
            form.add_error(
                None, e if isinstance(e, ValidationError) else "Tồn kho vừa thay đổi. Kiểm tra lại."
            )
    scope = scoped_branches(request)
    balances = (
        Stock.objects.filter(branch__in=scope)
        .select_related("branch", "product")
        .order_by("branch_id", "product__name")
    )
    query = request.GET.get("q", "").strip()[:100]
    if query:
        balances = balances.filter(
            Q(product__name__icontains=query) | Q(product__sku__icontains=query)
        )
    if request.GET.get("low") == "1":
        balances = balances.filter(quantity__lte=F("product__reorder_level"))
    history = StockMovement.objects.filter(stock__branch__in=scope).select_related(
        "stock__branch", "stock__product", "actor"
    )
    if request.GET.get("export") in ("xlsx", "pdf"):
        rows = [
            [s.branch.name, s.product.sku, s.product.name, s.quantity, s.product.unit]
            for s in balances[:5000]
        ]
        return download(
            request.GET["export"],
            "Tồn kho từng chi nhánh",
            ["Chi nhánh", "Mã", "Sản phẩm", "Tồn", "Đơn vị"],
            rows,
            "ton-kho",
        )
    return workspace(
        request,
        "Kho theo chi nhánh",
        {
            "mode": "stock",
            "form": form,
            "page_obj": paginate(request, balances),
            "movements": history[:50],
        },
    )


@branch_manager_required
@require_GET
def commissions(request):
    qs = (
        Commission.objects.filter(invoice__appointment__branch__in=scoped_branches(request))
        .select_related("employee__branch", "invoice__appointment", "invoice__refund")
        .order_by("-created_at")
    )
    start = request.GET.get("start", "")
    end = request.GET.get("end", "")
    from datetime import date

    try:
        if start:
            qs = qs.filter(created_at__date__gte=date.fromisoformat(start))
        if end:
            qs = qs.filter(created_at__date__lte=date.fromisoformat(end))
    except ValueError:
        messages.error(request, "Ngày lọc không hợp lệ.")
        qs = qs.none()
    total = qs.filter(invoice__refund__isnull=True).aggregate(n=Sum("amount"))["n"] or 0
    if request.GET.get("export") in ("xlsx", "pdf"):
        rows = [
            [
                c.employee.branch.name,
                c.employee.name,
                c.invoice.code,
                c.percent,
                0 if hasattr(c.invoice, "refund") else c.amount,
            ]
            for c in qs[:5000]
        ]
        return download(
            request.GET["export"],
            "Hoa hồng theo hóa đơn",
            ["Chi nhánh", "Stylist", "Hóa đơn", "Tỷ lệ %", "Hoa hồng"],
            rows,
            "hoa-hong",
        )
    return workspace(
        request,
        "Hoa hồng stylist",
        {"mode": "commissions", "page_obj": paginate(request, qs), "total": total},
    )


@branch_manager_required
@require_GET
def email_status(request):
    qs = (
        EmailOutbox.objects.filter(appointment__branch__in=scoped_branches(request))
        .select_related("appointment__branch")
        .order_by("-pk")
    )
    return workspace(
        request,
        "Xác nhận & nhắc lịch qua email",
        {"mode": "emails", "page_obj": paginate(request, qs)},
    )


@login_required
@require_GET
def stylist(request):
    if not request.user.is_stylist:
        raise PermissionDenied
    employee = Employee.objects.filter(
        account=request.user, branch_id=request.user.branch_id, active=True
    ).first()
    qs = (
        appointments_for(request.user)
        .filter(start_at__date=chosen_day(request))
        .order_by("start_at")
        if employee
        else Appointment.objects.none()
    )
    commissions = (
        Commission.objects.filter(
            employee=employee,
            invoice__refund__isnull=True,
            created_at__year=timezone.localdate().year,
            created_at__month=timezone.localdate().month,
        )
        if employee
        else Commission.objects.none()
    )
    shifts = (
        Shift.objects.filter(employee=employee, start_at__date=chosen_day(request))
        if employee
        else Shift.objects.none()
    )
    return page(
        request,
        "Lịch làm việc của tôi",
        "business/stylist.html",
        {
            "employee": employee,
            "shifts": shifts,
            "own_commission": commissions.aggregate(n=Sum("amount"))["n"] or 0,
            "day": chosen_day(request),
            "page_obj": paginate(request, qs),
        },
    )


@operator_required
@require_GET
def quote(request, pk):
    from django.http import JsonResponse

    a = get_object_or_404(appointments_for(request.user), pk=pk)
    raw = request.GET.get("points", "0")
    if not raw.isascii() or not raw.isdecimal() or len(raw) > 9:
        return JsonResponse({"error": "Số điểm không hợp lệ."}, status=400)
    try:
        total, discount, voucher = business.payment_quote(
            a, a.customer, int(raw), request.GET.get("voucher", "")[:40]
        )
    except ValidationError as e:
        return JsonResponse({"error": " ".join(e.messages)}, status=400)
    return JsonResponse({"total": total, "voucher_discount": discount})


@branch_manager_required
@require_GET
def branch_audit(request):
    scope = scoped_branches(request)
    qs = (
        AuditLog.objects.filter(Q(branch__in=scope) | Q(appointment__branch__in=scope))
        .select_related("actor", "branch", "appointment__branch")
        .distinct()
        .order_by("-created_at", "-pk")
    )
    query = request.GET.get("q", "").strip()[:100]
    if query:
        qs = qs.filter(Q(action__icontains=query) | Q(actor__full_name__icontains=query))
    return workspace(
        request,
        "Nhật ký trong phạm vi chi nhánh",
        {"mode": "audit", "page_obj": paginate(request, qs)},
    )


@operator_required
@require_http_methods(["GET", "POST"])
def customer_contact(request, pk):
    qs = User.objects.filter(role="customer")
    if not request.user.is_manager:
        qs = qs.filter(appointments__branch__in=branches_for(request.user)).distinct()
    customer = get_object_or_404(qs, pk=pk)
    form = CustomerContactForm(request.POST or None, instance=customer, actor=request.user)
    if request.method == "POST":
        try:
            with transaction.atomic():
                list(
                    Branch.objects.select_for_update()
                    .filter(pk__in=branches_for(request.user))
                    .order_by("pk")
                )
                current = get_object_or_404(User, pk=request.user.pk, is_active=True)
                if not current.is_operator:
                    raise PermissionDenied
                allowed = User.objects.filter(role="customer", pk=pk)
                if not current.is_manager:
                    allowed = allowed.filter(appointments__branch_id=current.branch_id)
                if not allowed.exists():
                    raise Http404
                phone = request.POST.get("phone", "").strip()
                if phone:
                    from django.db import connection

                    with connection.cursor() as cursor:
                        cursor.execute(
                            "SELECT pg_advisory_xact_lock(hashtext(%s))", ["walkin:" + phone]
                        )
                customer = User.objects.select_for_update().get(pk=pk)
                old_email = customer.email
                form = CustomerContactForm(request.POST, instance=customer, actor=current)
                if form.is_valid():
                    form.save()
                    if customer.email != old_email:
                        pending = EmailOutbox.objects.filter(
                            appointment__customer=customer, sent_at__isnull=True
                        )
                        if customer.email:
                            pending.update(recipient=customer.email)
                        else:
                            pending.update(cancelled=True)
                    AuditLog.objects.create(
                        actor=current,
                        branch=current.branch,
                        action=f"Xác minh và cập nhật liên hệ khách #{pk}",
                    )
                    messages.success(
                        request,
                        "Đã cập nhật liên hệ. Khách chưa có mật khẩu có thể yêu cầu liên kết kích hoạt qua email đã lưu.",
                    )
                    return redirect("customers")
        except IntegrityError:
            form.add_error(None, "Thông tin vừa thay đổi, vui lòng kiểm tra lại.")
    return form_page(
        request,
        "Thông tin liên hệ khách hàng",
        form,
        "Hồ sơ khách và điểm dùng chung toàn chuỗi. Chỉ cập nhật liên hệ sau xác minh; không thay tài khoản đăng nhập, vai trò, lịch sử hoặc điểm.",
    )


# Master data has controlled deletion; financial/stock/appointment histories are append-only.
RESOURCE_FORMS = {
    "chi-nhanh": (Branch, PolicyForm, "Chi nhánh & chính sách"),
    "stylist": (Employee, StylistForm, "Stylist & hoa hồng"),
    "ghe": (Chair, ChairForm, "Ghế cắt"),
    "ca-lam": (Shift, ShiftForm, "Ca làm"),
    "tai-khoan": (User, BranchAccountForm, "Tài khoản chi nhánh"),
    "san-pham": (Product, ProductForm, "Sản phẩm / vật tư"),
    "voucher": (Voucher, VoucherForm, "Voucher"),
}


def resource_scope(user, key):
    if key not in RESOURCE_FORMS:
        raise Http404
    model = RESOURCE_FORMS[key][0]
    qs = model.objects.all()
    relations = {
        Employee: ("branch", "account"),
        Chair: ("branch",),
        Shift: ("employee__branch",),
        User: ("branch",),
        Voucher: ("branch",),
    }
    if model in relations:
        qs = qs.select_related(*relations[model])
    if user.is_manager:
        return qs
    scope = branches_for(user)
    if model is Branch:
        return qs.filter(pk__in=scope)
    if model is Shift:
        return qs.filter(employee__branch__in=scope)
    if model is User:
        return qs.filter(branch__in=scope, role__in=["receptionist", "stylist"])
    if model is Product:
        return qs.none()
    return qs.filter(branch__in=scope)


def scoped_form(user, key, cls, data=None, instance=None):
    kwargs = {"instance": instance}
    if cls in (WalkInForm, StylistForm, VoucherForm):
        kwargs["user"] = user
    if cls is BranchAccountForm:
        kwargs["actor"] = user
    form = cls(data, **kwargs)
    if key == "ghe":
        form.fields["branch"].queryset = branches_for(user)
    if key == "ca-lam":
        form.fields["employee"].queryset = Employee.objects.filter(
            branch__in=branches_for(user), active=True
        )
    return form


@branch_manager_required
@require_GET
def resources(request, key):
    if key == "san-pham" and not request.user.is_manager:
        raise PermissionDenied
    model, cls, title = RESOURCE_FORMS.get(key, (None, None, None))
    if not model:
        raise Http404
    qs = resource_scope(request.user, key).order_by("-pk")
    if key == "chi-nhanh":
        qs = qs.order_by("pk")
    return workspace(
        request, title, {"mode": "resources", "key": key, "page_obj": paginate(request, qs)}
    )


@branch_manager_required
@require_http_methods(["GET", "POST"])
def resource_edit(request, key, pk=None):
    if key not in RESOURCE_FORMS:
        raise Http404
    if key == "san-pham" and not request.user.is_manager:
        raise PermissionDenied
    if key == "chi-nhanh" and pk is None and not request.user.is_manager:
        raise PermissionDenied
    model, cls, title = RESOURCE_FORMS[key]
    obj = get_object_or_404(resource_scope(request.user, key), pk=pk) if pk else None
    form = scoped_form(request.user, key, cls, request.POST or None, obj)
    if request.method == "POST":
        try:
            with transaction.atomic():
                # Same stable branch order as other admin operations; scope is rechecked inside lock.
                list(Branch.objects.select_for_update().order_by("pk"))
                request.user = get_object_or_404(User, pk=request.user.pk, is_active=True)
                if not request.user.can_manage_branch:
                    raise PermissionDenied
                if key == "san-pham" or (key == "chi-nhanh" and pk is None):
                    if not request.user.is_manager:
                        raise PermissionDenied
                if pk:
                    obj = get_object_or_404(
                        resource_scope(request.user, key).select_for_update(of=("self",)), pk=pk
                    )
                form = scoped_form(request.user, key, cls, request.POST, obj)
                if form.is_valid():
                    saved = form.save()
                    if model is Product:
                        Stock.objects.bulk_create(
                            [Stock(branch=b, product=saved) for b in Branch.objects.all()],
                            ignore_conflicts=True,
                        )
                    elif model is Branch:
                        Stock.objects.bulk_create(
                            [
                                Stock(branch=saved, product=p)
                                for p in Product.objects.filter(active=True)
                            ],
                            ignore_conflicts=True,
                        )
                    AuditLog.objects.create(
                        actor=request.user,
                        branch=request.user.branch if not request.user.is_manager else None,
                        action=f"Lưu {key} #{saved.pk}",
                    )
                    messages.success(request, "Đã lưu dữ liệu.")
                    return redirect("business_resources", key=key)
        except (ValidationError, IntegrityError) as e:
            form.add_error(
                None, e if isinstance(e, ValidationError) else "Dữ liệu trùng hoặc đã thay đổi."
            )
    return form_page(
        request,
        "Cập nhật " + title,
        form,
        "Phạm vi dữ liệu được kiểm tra ở máy chủ; ngừng hoạt động để bảo toàn lịch sử đã phát sinh.",
    )


@branch_manager_required
@require_http_methods(["GET", "POST"])
def resource_delete(request, key, pk):
    if key not in RESOURCE_FORMS:
        raise Http404
    if key == "san-pham" and not request.user.is_manager:
        raise PermissionDenied
    model, _, title = RESOURCE_FORMS[key]
    obj = get_object_or_404(resource_scope(request.user, key), pk=pk)
    form = ConfirmDeleteForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                list(Branch.objects.select_for_update().order_by("pk"))
                request.user = get_object_or_404(User, pk=request.user.pk, is_active=True)
                if not request.user.can_manage_branch:
                    raise PermissionDenied
                if key == "san-pham" and not request.user.is_manager:
                    raise PermissionDenied
                obj = get_object_or_404(
                    resource_scope(request.user, key).select_for_update(of=("self",)), pk=pk
                )
                from .management_views import guard_delete
                from types import SimpleNamespace

                guard_delete(SimpleNamespace(model=model), obj, request.user)
                obj.delete()
                AuditLog.objects.create(
                    actor=request.user,
                    branch=request.user.branch if not request.user.is_manager else None,
                    action=f"Xóa {key} #{pk}",
                )
            messages.success(request, "Đã xóa bản ghi chưa sử dụng.")
            return redirect("business_resources", key=key)
        except (ProtectedError, ValidationError, IntegrityError):
            form.add_error(
                None, "Bản ghi đã được sử dụng hoặc đang có lịch. Hãy ngừng hoạt động thay vì xóa."
            )
    return form_page(
        request,
        "Xóa " + title,
        form,
        "Chỉ xóa bản ghi chưa phát sinh liên kết; không xóa lịch sử giao dịch.",
    )


urlpatterns = [
    path(
        "quan-ly/khach-hang/<int:pk>/lien-he/", customer_contact, name="business_customer_contact"
    ),
    path("quan-ly/nhat-ky-chi-nhanh/", branch_audit, name="business_audit"),
    path("lich-hen/<int:pk>/bao-gia/", quote, name="business_quote"),
    path("quan-ly/van-hanh/", board, name="business_board"),
    path("quan-ly/tiep-nhan/", walkin, name="business_walkin"),
    path("quan-ly/lich-nghi/", interruptions, name="business_interruptions"),
    path(
        "quan-ly/lich-nghi/<slug:kind>/<int:pk>/ngung/",
        toggle_interruption,
        name="business_stop_interruption",
    ),
    path("quan-ly/chot-so/", closing, name="business_closing"),
    path("quan-ly/kho/", stock, name="business_stock"),
    path("quan-ly/hoa-hong/", commissions, name="business_commissions"),
    path("quan-ly/email/", email_status, name="business_emails"),
    path("quan-ly/tai-nguyen/<slug:key>/", resources, name="business_resources"),
    path("quan-ly/tai-nguyen/<slug:key>/them/", resource_edit, name="business_resource_add"),
    path(
        "quan-ly/tai-nguyen/<slug:key>/<int:pk>/sua/", resource_edit, name="business_resource_edit"
    ),
    path(
        "quan-ly/tai-nguyen/<slug:key>/<int:pk>/xoa/",
        resource_delete,
        name="business_resource_delete",
    ),
    path("lich-hen/<int:pk>/dieu-chinh/<slug:kind>/", adjust, name="business_adjust"),
    path("quan-ly/hoa-don/<int:pk>/hoan-tien/", refund, name="business_refund"),
    path("stylist/", stylist, name="stylist_portal"),
]
