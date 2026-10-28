import os, sys, uuid
from pathlib import Path
from datetime import timedelta, time
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django

django.setup()
from django.conf import settings
from urllib.parse import urlsplit

BASE = os.getenv("APP_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
if not settings.DEBUG or urlsplit(BASE).hostname not in ("localhost", "127.0.0.1"):
    raise SystemExit("Run only on a local DEBUG demo database.")
from django.utils import timezone
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from salon.models import (
    User,
    Branch,
    Employee,
    Shift,
    Chair,
    Appointment,
    AppointmentItem,
    Invoice,
    PointEntry,
    Notification,
    AuditLog,
    Review,
    Service,
    Commission,
    VoucherUse,
    Refund,
    AppointmentChange,
    EmailOutbox,
)
from salon.services import book, local_at
from playwright.sync_api import sync_playwright, expect

marker = "completion-" + uuid.uuid4().hex[:8]
password = "Completion@Test2026"
new_password = "Reset@Complete2026"
manager = User.objects.create_user(
    username=marker, password=password, role="manager", full_name="Quản trị kiểm thử"
)
customer = User.objects.create_user(
    username=marker + "-c",
    password=password,
    full_name="Khách kiểm thử",
    email=marker + "@example.invalid",
    phone="0901234567",
    points=50,
)
branch = Branch.objects.create(
    name=marker, address="TP.HCM", phone="0901234567", opens_at=time(9), closes_at=time(21)
)
employee = Employee.objects.create(name=marker, branch=branch, specialty="Fade")
Chair.objects.create(branch=branch, name="Ghế kiểm thử")
day = timezone.localdate() + timedelta(days=1)
Shift.objects.create(
    employee=employee, start_at=local_at(day, time(9)), end_at=local_at(day, time(21))
)
a = book(
    customer=customer,
    branch_id=branch.pk,
    employee_id=employee.pk,
    service_ids=[Service.objects.first().pk],
    start=local_at(day, time(10)),
)
a.status = "awaiting_payment"
a.save(update_fields=["status"])
uid = urlsafe_base64_encode(force_bytes(customer.pk))
token = default_token_generator.make_token(customer)
mail_dir = Path(settings.EMAIL_FILE_PATH)
before = set(mail_dir.glob("*")) if mail_dir.exists() else set()
pool = ThreadPoolExecutor(max_workers=1)


def db(fn):
    def run():
        from django.db import connections

        try:
            return fn()
        finally:
            connections.close_all()

    return pool.submit(run).result()


errors = []
output = ROOT / "test-results/completion"
output.mkdir(parents=True, exist_ok=True)
try:
    with sync_playwright() as p:
        options = {"args": ["--no-sandbox"]}
        if os.getenv("BROWSER_EXECUTABLE"):
            options["executable_path"] = os.environ["BROWSER_EXECUTABLE"]
        browser = p.chromium.launch(**options)
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, locale="vi-VN")
        page.on("pageerror", lambda e: errors.append(str(e)))
        base = BASE
        if settings.EMAIL_BACKEND.endswith("filebased.EmailBackend"):
            page.goto(base + "/quen-mat-khau/")
            page.locator("#id_email").fill(customer.email)
            page.get_by_role("button", name="Gửi liên kết đặt lại", exact=True).click()
            page.wait_for_url("**/quen-mat-khau/da-gui/")
            assert set(mail_dir.glob("*")) - before
        page.goto(base + f"/dat-lai-mat-khau/{uid}/{token}/")
        page.locator("#id_new_password1").fill(new_password)
        page.locator("#id_new_password2").fill(new_password)
        page.get_by_role("button", name="Lưu mật khẩu mới", exact=True).click()
        page.wait_for_url("**/dat-lai-mat-khau/hoan-tat/")

        def login(user, pw):
            page.goto(base + "/dang-nhap/")
            page.locator("#id_username").fill(user)
            page.locator("#id_password").fill(pw)
            page.get_by_role("button", name="Đăng nhập", exact=True).click()
            page.wait_for_url("**/quan-ly/" if user == marker else "**/lich-cua-toi/")

        def logout():
            page.goto(base + "/")
            page.get_by_role("button", name="Đăng xuất", exact=True).click()

        login(customer.username, new_password)
        page.goto(base + "/thong-bao/")
        expect(page.get_by_role("link", name="Xem lịch hẹn", exact=True)).to_be_visible()
        page.get_by_role("button", name="Đánh dấu tất cả đã đọc", exact=True).click()
        page.locator("#notification-state").select_option("unread")
        page.get_by_role("button", name="Lọc thông báo").click()
        expect(page.locator("main")).to_contain_text("Chưa có thông báo phù hợp")
        logout()
        login(marker, password)
        page.goto(base + f"/lich-hen/{a.pk}/")
        page.locator("#redeem-points").fill("10")
        expect(page.locator("#payment-preview")).to_contain_text("Cần thu:")
        page.on("dialog", lambda dialog: dialog.accept())
        page.get_by_role("button", name="Xác nhận thu tiền ✓", exact=True).click()
        page.wait_for_url(base + f"/lich-hen/{a.pk}/")
        invoice = db(lambda: Invoice.objects.get(appointment_id=a.pk))
        assert invoice.discount == 10000
        page.goto(base + "/quan-ly/nhat-ky/?q=" + marker)
        expect(page.get_by_role("button", name="Tra cứu nhật ký", exact=True)).to_be_visible()
        for width in (320, 390, 768, 1440):
            page.set_viewport_size({"width": width, "height": 900})
            for route in ["/quan-ly/nhat-ky/", "/quan-ly/lich-tuan/", "/quan-ly/hieu-qua/"]:
                page.goto(base + route)
                assert page.locator("html").evaluate("(el)=>el.scrollWidth") <= width, (
                    route,
                    width,
                )
        page.set_viewport_size({"width": 1440, "height": 1000})
        page.goto(base + "/quan-ly/hieu-qua/")
        with page.expect_download() as download:
            page.get_by_role("link", name="Xuất Excel", exact=True).click()
        assert download.value.suggested_filename.endswith(".xlsx")
        with page.expect_download() as download:
            page.get_by_role("link", name="Xuất PDF", exact=True).click()
        assert download.value.suggested_filename.endswith(".pdf")
        page.screenshot(path=str(output / "performance.png"), full_page=True)
        logout()
        login(customer.username, new_password)
        page.goto(base + "/diem-tich-luy/")
        expect(page.locator("main")).to_contain_text("Sử dụng điểm")
        page.screenshot(path=str(output / "points.png"), full_page=True)
        assert not errors, errors
        browser.close()
    print(
        "PASS: reset token + login (local email when enabled), notification ownership/read UI, checkout point preview/payment/net invoice, history, weekly/audit/performance responsive screens, XLSX/PDF downloads; no JS errors."
    )
finally:
    pool.shutdown()
    PointEntry.objects.filter(customer=customer).delete()
    VoucherUse.objects.filter(invoice__appointment_id=a.pk).delete()
    Refund.objects.filter(invoice__appointment_id=a.pk).delete()
    Commission.objects.filter(invoice__appointment_id=a.pk).delete()
    AppointmentChange.objects.filter(appointment_id=a.pk).delete()
    EmailOutbox.objects.filter(appointment_id=a.pk).delete()
    Invoice.objects.filter(appointment_id=a.pk).delete()
    Review.objects.filter(appointment_id=a.pk).delete()
    AuditLog.objects.filter(actor__in=[manager, customer]).delete()
    AuditLog.objects.filter(appointment_id=a.pk).delete()
    Notification.objects.filter(recipient=customer).delete()
    Appointment.objects.filter(pk=a.pk).delete()
    Shift.objects.filter(employee=employee).delete()
    employee.delete()
    Chair.objects.filter(branch=branch).delete()
    branch.delete()
    customer.delete()
    manager.delete()
    if mail_dir.exists():
        for path in set(mail_dir.glob("*")) - before:
            if marker in path.read_text():
                path.unlink()
