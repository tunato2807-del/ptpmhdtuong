"""Local DEBUG acceptance flow for multi-branch operations; removes only own fixtures."""

import os, sys, uuid
from pathlib import Path
from datetime import timedelta, time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django

django.setup()
from django.conf import settings
from django.test import Client
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.db import connections
from salon.models import (
    Branch,
    User,
    Employee,
    Chair,
    Shift,
    Service,
    Appointment,
    AppointmentItem,
    Invoice,
    PointEntry,
    Commission,
    Refund,
    Voucher,
    VoucherUse,
    Stock,
    StockMovement,
    Product,
    DailyClosing,
    AppointmentChange,
    EmployeeAbsence,
    BranchClosure,
    EmailOutbox,
    Notification,
    AuditLog,
    Review,
)
from salon.services import book, local_at
from playwright.sync_api import sync_playwright, expect

BASE = os.getenv("APP_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
if not settings.DEBUG or urlsplit(BASE).hostname not in ("localhost", "127.0.0.1"):
    raise SystemExit("Local DEBUG checkout/database only.")
marker = "business-" + uuid.uuid4().hex[:8]
phone = "09" + str(uuid.uuid4().int % 100000000).zfill(8)
branches = [
    Branch.objects.create(
        name=marker + " " + letter,
        address="Chi nhánh kiểm thử " + letter,
        phone="0901234567",
        opens_at=time(0),
        closes_at=time(23, 59),
    )
    for letter in ("A", "B")
]
manager = User.objects.create_user(
    username=marker + "-manager", full_name="Quản trị toàn chuỗi", role="manager"
)
boss = User.objects.create_user(
    username=marker + "-boss", full_name="Quản lý A", role="branch_manager", branch=branches[0]
)
boss_b = User.objects.create_user(
    username=marker + "-boss-b", full_name="Quản lý B", role="branch_manager", branch=branches[1]
)
stylist = User.objects.create_user(
    username=marker + "-stylist", full_name="Stylist A", role="stylist", branch=branches[0]
)
employees = [
    Employee.objects.create(
        name=marker + " Stylist " + str(i),
        branch=branches[0 if i < 2 else 1],
        specialty="Cắt và gội",
        commission_percent=20,
        account=stylist if i == 0 else None,
    )
    for i in range(3)
]
chairs = [Chair.objects.create(branch=b, name="Ghế 1") for b in branches]
Chair.objects.create(branch=branches[0], name="Ghế 2")
for e in employees:
    for offset in (0, 1):
        day = timezone.localdate() + timedelta(days=offset)
        Shift.objects.create(
            employee=e, start_at=local_at(day, time(0)), end_at=local_at(day, time(23, 59))
        )
services = [
    Service.objects.create(name=marker + " Cắt", kind="hair", price=100000, duration=15),
    Service.objects.create(name=marker + " Gội", kind="care", price=50000, duration=15),
]
product = Product.objects.create(sku=marker, name="Sáp kiểm thử", reorder_level=2)
voucher = Voucher.objects.create(
    code=marker.upper(),
    branch=branches[0],
    amount=20000,
    starts_at=timezone.now() - timedelta(days=1),
    ends_at=timezone.now() + timedelta(days=1),
    max_uses=5,
)
sessions = {}
for role, user in [("manager", manager), ("boss", boss), ("boss_b", boss_b), ("stylist", stylist)]:
    client = Client()
    client.force_login(user)
    sessions[role] = client.session.session_key
pool = ThreadPoolExecutor(max_workers=1)


def db(fn):
    def run():
        try:
            return fn()
        finally:
            connections.close_all()

    return pool.submit(run).result()


output = ROOT / "test-results/business"
output.mkdir(parents=True, exist_ok=True)
errors = []
checks = 0
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=os.getenv("BROWSER_EXECUTABLE", "/usr/bin/chromium"),
            args=["--no-sandbox"],
        )
        context = browser.new_context(locale="vi-VN", viewport={"width": 1440, "height": 1000})
        page = context.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("dialog", lambda d: d.accept())
        page.on(
            "response",
            lambda r: (
                errors.append(f"{r.status} {r.url}")
                if r.status >= 500 or (r.status >= 400 and "/static/" in r.url)
                else None
            ),
        )

        def switch(role):
            context.clear_cookies()
            context.add_cookies(
                [{"name": settings.SESSION_COOKIE_NAME, "value": sessions[role], "url": BASE}]
            )

        def save():
            page.get_by_role("button", name="Xác nhận và lưu", exact=True).click()

        def stock_move(role, kind, amount, target=None):
            switch(role)
            page.goto(BASE + "/quan-ly/kho/")
            page.locator("#id_branch").select_option(str(branches[0].pk))
            page.locator("#id_product").select_option(str(product.pk))
            page.locator("#id_kind").select_option(kind)
            page.locator("#id_amount").fill(str(amount))
            page.locator("#id_reason").fill("Chứng từ kiểm thử")
            if target:
                page.locator("#id_target").select_option(str(target))
            save()
            expect(page.locator(".messages")).to_contain_text("Đã ghi giao dịch kho")

        switch("boss")
        page.goto(BASE + "/quan-ly/tiep-nhan/")
        page.locator("#id_branch").select_option(str(branches[0].pk))
        page.locator("#id_name").fill(marker + " Khách")
        page.locator("#id_phone").fill(phone)
        page.locator("#id_email").fill(marker + "@example.invalid")
        page.locator("#id_employee").select_option(str(employees[0].pk))
        page.locator('input[name=services][value="' + str(services[0].pk) + '"]').check()
        now = timezone.localtime()
        start = now.replace(second=0, microsecond=0) + timedelta(minutes=15 - now.minute % 15)
        if start.date() != now.date() or start.time() > time(23, 15):
            raise AssertionError(
                "Run the acceptance flow with at least 45 minutes remaining in the day."
            )
        page.locator("#id_start").fill(start.strftime("%Y-%m-%dT%H:%M"))
        save()
        page.wait_for_url("**/lich-hen/*/")
        pk = int(urlsplit(page.url).path.strip("/").split("/")[-1])
        appt_url = BASE + f"/lich-hen/{pk}/"
        customer_pk = db(lambda: Appointment.objects.get(pk=pk).customer_id)
        page.goto(BASE + f"/quan-ly/khach-hang/{customer_pk}/lien-he/")
        page.locator("#id_verified").check()
        save()
        expect(page.locator(".messages")).to_contain_text("Đã cập nhật liên hệ")
        page.goto(appt_url)
        page.locator("#chair").select_option(str(chairs[0].pk))
        page.get_by_role("button", name="Check-in khách hàng ✓", exact=True).click()
        expect(page.locator(".badge.large")).to_contain_text("Đã check-in")
        switch("stylist")
        page.goto(appt_url)
        page.get_by_role("button", name="Bắt đầu phục vụ →", exact=True).click()
        expect(page.locator(".badge.large")).to_contain_text("Đang phục vụ")
        switch("boss")
        page.goto(BASE + f"/lich-hen/{pk}/dieu-chinh/dich-vu/")
        for s in services:
            page.locator('input[name=services][value="' + str(s.pk) + '"]').check()
        page.locator("#id_reason").fill("Khách đồng ý thêm gội")
        page.locator("#id_confirm").check()
        save()
        page.wait_for_url(appt_url)
        switch("stylist")
        page.goto(appt_url)
        page.get_by_role("button", name="Hoàn tất phục vụ ✓", exact=True).click()
        expect(page.locator(".badge.large")).to_contain_text("Chờ thanh toán")
        switch("boss")
        page.goto(appt_url)
        page.locator("#voucher-code").fill(voucher.code)
        expect(page.locator("#payment-preview")).to_contain_text("130.000")
        page.get_by_role("button", name="Xác nhận thu tiền ✓", exact=True).click()
        expect(page.locator(".badge.large")).to_contain_text("Đã thanh toán")
        inv = db(lambda: Invoice.objects.get(appointment_id=pk))
        assert inv.total == 130000
        assert db(lambda: Commission.objects.get(invoice_id=inv.pk).amount) == 26000
        page.get_by_role("link", name="Xem hóa đơn").click()
        with page.expect_download() as dl:
            page.get_by_role("link", name="Tải PDF", exact=True).click()
        assert dl.value.suggested_filename.endswith(".pdf")
        stock_move("boss", "receipt", 5)
        stock_move("manager", "transfer", 2, branches[1].pk)
        assert db(lambda: Stock.objects.get(branch=branches[0], product=product).quantity) == 3
        assert db(lambda: Stock.objects.get(branch=branches[1], product=product).quantity) == 2
        switch("boss_b")
        response = page.goto(appt_url)
        assert response.status == 404
        page.goto(BASE + "/quan-ly/kho/")
        expect(page.locator(".business-table")).not_to_contain_text(branches[0].name)
        # Add an isolated future fixture, then resolve its interruption through the actual UI.
        tomorrow = timezone.localdate() + timedelta(days=1)

        def future_booking():
            customer = Appointment.objects.get(pk=pk).customer
            return book(
                customer=customer,
                actor=boss,
                branch_id=branches[0].pk,
                employee_id=employees[0].pk,
                service_ids=[services[0].pk],
                start=local_at(tomorrow, time(10)),
            ).pk

        future_pk = db(future_booking)
        switch("boss")
        page.goto(BASE + "/quan-ly/lich-nghi/")
        page.locator("#id_branch").select_option(str(branches[0].pk))
        page.locator("#id_employee").select_option(str(employees[0].pk))
        page.locator("#id_start").fill(tomorrow.strftime("%Y-%m-%d") + "T09:00")
        page.locator("#id_end").fill(tomorrow.strftime("%Y-%m-%d") + "T12:00")
        page.locator("#id_reason").fill("Nghỉ đột xuất, cần điều phối")
        page.locator("#id_confirm").check()
        save()
        expect(page.locator(".business-table")).to_contain_text(f"LH{future_pk:05d}")
        page.goto(BASE + f"/lich-hen/{future_pk}/doi-lich/")
        page.locator("#id_employee").select_option(str(employees[1].pk))
        page.get_by_role("button", name="Xem giờ trống", exact=True).click()
        page.locator("#id_time").select_option("10:00")
        page.get_by_role("button", name="Lưu lịch mới", exact=True).click()
        page.wait_for_url(BASE + f"/lich-hen/{future_pk}/")
        assert db(lambda: Appointment.objects.get(pk=future_pk).employee_id) == employees[1].pk
        # All operational pages: no horizontal page overflow or missing logout.
        routes = [
            "/quan-ly/van-hanh/",
            "/quan-ly/tiep-nhan/",
            "/quan-ly/lich-nghi/",
            "/quan-ly/chot-so/",
            "/quan-ly/kho/",
            "/quan-ly/hoa-hong/",
            "/quan-ly/email/",
            "/quan-ly/nhat-ky-chi-nhanh/",
        ]
        for width in (320, 390, 768, 1024, 1440, 1920):
            page.set_viewport_size({"width": width, "height": 900})
            for route in routes:
                response = page.goto(BASE + route)
                assert response.status == 200, (route, response.status)
                page.evaluate("document.fonts.ready")
                assert page.locator("html").evaluate("(e)=>e.scrollWidth") <= width, (route, width)
                expect(page.get_by_role("button", name="Đăng xuất", exact=True)).to_be_visible()
                checks += 1
        page.set_viewport_size({"width": 1440, "height": 1000})
        page.goto(BASE + "/quan-ly/van-hanh/")
        page.evaluate("document.fonts.ready")
        page.wait_for_timeout(700)
        page.screenshot(path=str(output / "branch-board.png"), full_page=True)
        switch("manager")
        page.goto(BASE + "/quan-ly/van-hanh/")
        page.evaluate("document.fonts.ready")
        page.wait_for_timeout(700)
        page.screenshot(path=str(output / "chain-board.png"), full_page=True)
        switch("boss")
        page.goto(BASE + "/quan-ly/hoa-hong/")
        page.wait_for_timeout(700)
        page.screenshot(path=str(output / "commissions.png"), full_page=True)
        for route in ["/quan-ly/van-hanh/", "/quan-ly/kho/", "/quan-ly/hoa-hong/"]:
            for fmt in ("xlsx", "pdf"):
                response = page.request.get(BASE + route + "?export=" + fmt)
                assert response.status == 200, (route, fmt, response.status)
        # Refund and close the day after resolving all amounts.
        page.goto(BASE + f"/quan-ly/hoa-don/{inv.pk}/hoan-tien/")
        page.locator("#id_reason").fill("Đã trả đủ tiền theo yêu cầu khách")
        page.locator("#id_confirm").check()
        save()
        expect(page.locator(".messages")).to_contain_text("Đã ghi nhận hoàn tiền")
        page.goto(BASE + "/quan-ly/chot-so/")
        page.locator("#id_branch").select_option(str(branches[0].pk))
        page.locator("#id_day").fill(str(timezone.localdate()))
        page.locator("#id_counted").fill("0")
        page.locator("#id_confirm").check()
        save()
        expect(page.locator(".messages")).to_contain_text("Đã chốt sổ")
        assert db(lambda: DailyClosing.objects.get(branch=branches[0]).expected_cash) == 0
        switch("stylist")
        page.goto(BASE + "/stylist/")
        expect(page.locator("main")).to_contain_text(employees[0].name)
        assert not errors, errors
        browser.close()
    print(
        f"PASS: walk-in, branch scope, stylist start/finish, service change, voucher quote/payment, commission snapshot, invoice PDF, stock receipt/transfer, absence resolution, refund/closing, {checks} responsive operational views, exports; no JS/asset errors."
    )
finally:
    pool.shutdown()
    Session.objects.filter(session_key__in=sessions.values()).delete()
    appts = Appointment.objects.filter(branch__in=branches)
    invoices = Invoice.objects.filter(appointment__in=appts)
    users = User.objects.filter(username__startswith=marker)
    # The walk-in customer username is random; identify only by this run's unique phone.
    customers = User.objects.filter(phone=phone, role="customer")
    PointEntry.objects.filter(customer__in=customers).delete()
    VoucherUse.objects.filter(invoice__in=invoices).delete()
    Refund.objects.filter(invoice__in=invoices).delete()
    Commission.objects.filter(invoice__in=invoices).delete()
    DailyClosing.objects.filter(branch__in=branches).delete()
    Invoice.objects.filter(pk__in=invoices.values("pk")).delete()
    Review.objects.filter(appointment__in=appts).delete()
    AppointmentChange.objects.filter(appointment__in=appts).delete()
    EmailOutbox.objects.filter(appointment__in=appts).delete()
    AuditLog.objects.filter(branch__in=branches).delete()
    AuditLog.objects.filter(appointment__in=appts).delete()
    AuditLog.objects.filter(actor__in=users).delete()
    Notification.objects.filter(appointment__in=appts).delete()
    appts.delete()
    EmployeeAbsence.objects.filter(employee__in=employees).delete()
    BranchClosure.objects.filter(branch__in=branches).delete()
    StockMovement.objects.filter(stock__branch__in=branches).delete()
    Stock.objects.filter(branch__in=branches).delete()
    Shift.objects.filter(employee__in=employees).delete()
    Employee.objects.filter(pk__in=[e.pk for e in employees]).delete()
    Chair.objects.filter(branch__in=branches).delete()
    Voucher.objects.filter(pk=voucher.pk).delete()
    Product.objects.filter(pk=product.pk).delete()
    users.delete()
    customers.delete()
    Branch.objects.filter(pk__in=[b.pk for b in branches]).delete()
    Service.objects.filter(pk__in=[s.pk for s in services]).delete()
