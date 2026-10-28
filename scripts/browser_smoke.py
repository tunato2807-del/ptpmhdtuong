"""Run against the local demo server only. Cleans up its own test user and records.

Usage: .venv/bin/python scripts/browser_smoke.py
Optional BROWSER_EXECUTABLE=/path/to/chromium, APP_BASE_URL=http://127.0.0.1:8000
"""

import os
import sys
import uuid
from datetime import datetime, timedelta, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django

django.setup()
from django.conf import settings
from django.contrib.sessions.models import Session
from salon.models import (
    User,
    Appointment,
    Invoice,
    Review,
    AuditLog,
    Notification,
    PointEntry,
    Commission,
    Refund,
    VoucherUse,
    AppointmentChange,
    EmailOutbox,
    Branch,
    Employee,
    Chair,
    Shift,
)
from playwright.sync_api import sync_playwright, expect

BASE_URL = os.getenv("APP_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
if not settings.DEBUG or urlsplit(BASE_URL).hostname not in ("127.0.0.1", "localhost"):
    raise SystemExit(
        "Browser smoke requires DEBUG=1 and a local demo server using this checkout/database."
    )
username = "smoke-" + uuid.uuid4().hex[:12]
password = "Browser@Test2026"
output = ROOT / "test-results"
output.mkdir(exist_ok=True)
screenshots = output / "journey"
screenshots.mkdir(exist_ok=True, parents=True)
today = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date()
errors = []
session_keys = set()
# Isolated round-the-clock branch: the check-in acceptance flow must not depend
# on the demo branch opening at 09:00 when the test runs overnight.
from salon.services import local_at

fixture_branch = Branch.objects.create(
    name=username + " Chi nhánh",
    address="Chi nhánh kiểm thử",
    phone="0901234567",
    opens_at=time(0),
    closes_at=time(23, 59),
)
fixture_employee = Employee.objects.create(name="Stylist kiểm thử", branch=fixture_branch)
fixture_chair = Chair.objects.create(name="Ghế kiểm thử", branch=fixture_branch)
for offset in (0, 1, 2):
    fixture_day = today + timedelta(days=offset)
    Shift.objects.create(
        employee=fixture_employee,
        start_at=local_at(fixture_day, time(0)),
        end_at=local_at(fixture_day, time(23, 59)),
    )
fixture_reception = User.objects.create_user(
    username=username + "-reception", password=password, role="receptionist", branch=fixture_branch
)
fixture_manager = User.objects.create_user(
    username=username + "-manager", password=password, role="manager"
)


def cleanup():
    user = User.objects.filter(username=username).first()
    if not user:
        return
    appointments = Appointment.objects.filter(customer=user)
    PointEntry.objects.filter(customer=user).delete()
    VoucherUse.objects.filter(invoice__appointment__in=appointments).delete()
    Refund.objects.filter(invoice__appointment__in=appointments).delete()
    Commission.objects.filter(invoice__appointment__in=appointments).delete()
    AppointmentChange.objects.filter(appointment__in=appointments).delete()
    EmailOutbox.objects.filter(appointment__in=appointments).delete()
    Invoice.objects.filter(appointment__in=appointments).delete()
    Review.objects.filter(appointment__in=appointments).delete()
    AuditLog.objects.filter(appointment__in=appointments).delete()
    Notification.objects.filter(recipient=user).delete()
    appointments.delete()
    user.delete()


def sign_in(page, name, pw="Gentleman@2026"):
    page.goto(BASE_URL + "/dang-nhap/")
    page.locator("#id_username").fill(name)
    page.locator("#id_password").fill(pw)
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_url(
        "**/quan-ly/"
        if name in [fixture_manager.username, fixture_reception.username]
        else "**/lich-cua-toi/"
    )
    session_keys.update(
        c["value"] for c in page.context.cookies() if c["name"] == settings.SESSION_COOKIE_NAME
    )


def sign_out(page):
    page.goto(BASE_URL + "/")
    page.get_by_role("button", name="Đăng xuất").click()
    page.wait_for_url(BASE_URL + "/")


def choose_booking(page, day):
    page.goto(BASE_URL + "/dat-lich/")
    page.locator("#id_branch").select_option(str(fixture_branch.pk))
    page.locator("input[name=services]").first.check()
    page.locator("#id_employee").select_option(str(fixture_employee.pk))
    page.locator("#id_date").fill(day.isoformat())
    page.locator("#id_note").fill("Kiểm thử trình duyệt · dữ liệu tự xóa")
    first_slot = page.locator(".slot-button").first
    expect(first_slot).to_be_visible()
    first_slot.click()
    expect(page.locator("#submit-booking")).to_be_enabled()


try:
    with sync_playwright() as p:
        options = {"headless": True, "args": ["--no-sandbox", "--disable-dev-shm-usage"]}
        if os.getenv("BROWSER_EXECUTABLE"):
            options["executable_path"] = os.environ["BROWSER_EXECUTABLE"]
        browser = p.chromium.launch(**options)
        context = browser.new_context(viewport={"width": 1440, "height": 1000}, locale="vi-VN")
        page = context.new_page()
        page.set_default_timeout(15000)
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("dialog", lambda dialog: dialog.accept())
        page.goto(BASE_URL + "/")
        expect(page.get_by_role("heading", level=1)).to_contain_text("Một đường cắt.")
        page.screenshot(path=str(screenshots / "home-desktop.png"), full_page=True)
        page.goto(BASE_URL + "/dang-ky/")
        for key, value in {
            "full_name": "Khách kiểm thử",
            "username": username,
            "phone": "0909988776",
            "email": username + "@example.com",
            "password1": password,
            "password2": password,
        }.items():
            page.locator("#id_" + key).fill(value)
        page.get_by_role("button", name="Tạo tài khoản").click()
        page.wait_for_url("**/dat-lich/")
        session_keys.update(
            c["value"] for c in context.cookies() if c["name"] == settings.SESSION_COOKIE_NAME
        )
        choose_booking(page, today + timedelta(days=2))
        page.evaluate("window.scrollTo(0,0); document.activeElement.blur()")
        page.screenshot(path=str(screenshots / "booking-desktop.png"), full_page=True)
        page.locator("#submit-booking").click()
        page.wait_for_url("**/lich-hen/*/")
        page.get_by_role("link", name="Hủy lịch hẹn", exact=True).click()
        page.locator("#id_confirm").check()
        page.get_by_role("button", name="Xác nhận hủy", exact=True).click()
        expect(page.locator(".badge.large")).to_contain_text("Đã hủy")
        # A real "book today" flow has no slots after closing time. Keep UI booking
        # in the future, then prepare ONLY our own fixture for same-day check-in.
        choose_booking(page, today + timedelta(days=1))
        page.locator("#submit-booking").click()
        page.wait_for_url("**/lich-hen/*/")
        appointment_url = page.url
        appointment_pk = int(urlsplit(appointment_url).path.strip("/").split("/")[-1])

        def prepare_checkin():
            from django.db import connections
            from salon.services import local_at
            from datetime import time

            try:
                own = Appointment.objects.get(pk=appointment_pk, customer__username=username)
                duration = own.end_at - own.start_at
                from django.utils import timezone

                now = timezone.localtime()
                rounded = now.replace(second=0, microsecond=0) + timedelta(
                    minutes=15 - now.minute % 15
                )
                cursor = max(local_at(today, own.branch.opens_at), rounded)
                closing = local_at(today, own.branch.closes_at)
                while cursor + duration <= closing:
                    if (
                        not Appointment.objects.filter(
                            employee=own.employee,
                            status__in=["booked", "checked_in", "in_service"],
                            start_at__lt=cursor + duration,
                            end_at__gt=cursor,
                        )
                        .exclude(pk=own.pk)
                        .exists()
                    ):
                        Appointment.objects.filter(pk=own.pk, customer__username=username).update(
                            start_at=cursor, end_at=cursor + duration
                        )
                        return
                    cursor += timedelta(minutes=15)
                raise AssertionError("No free fixture interval for check-in.")
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=1) as fixture_pool:
            fixture_pool.submit(prepare_checkin).result()
        sign_out(page)
        sign_in(page, fixture_reception.username, password)
        page.goto(appointment_url)
        page.locator("#chair").select_option(str(fixture_chair.pk))
        page.get_by_role("button", name="Check-in khách hàng").click()
        expect(page.locator(".badge.large")).to_contain_text("Đã check-in")
        page.get_by_role("button", name="Bắt đầu phục vụ").click()
        expect(page.locator(".badge.large")).to_contain_text("Đang phục vụ")
        page.get_by_role("button", name="Hoàn tất phục vụ ✓", exact=True).click()
        expect(page.locator(".badge.large")).to_contain_text("Chờ thanh toán")
        page.locator("#method").select_option("mock")
        page.locator("input[name=confirmation]").check()
        page.get_by_role("button", name="Xác nhận thu tiền ✓", exact=True).click()
        expect(page.locator(".badge.large")).to_contain_text("Đã thanh toán")
        page.get_by_role("link", name="Xem hóa đơn").click()
        expect(page.locator("h1")).to_contain_text("Hóa đơn dịch vụ")
        expect(page.locator(".invoice-paper")).to_contain_text("giao dịch mô phỏng")
        page.screenshot(path=str(output / "invoice.png"), full_page=True)
        sign_out(page)
        sign_in(page, username, password)
        page.goto(appointment_url)
        page.locator("#id_rating").select_option("5")
        page.locator("#id_comment").fill("Trải nghiệm kiểm thử thành công.")
        page.get_by_role("button", name="Gửi đánh giá").click()
        expect(page.locator(".review-display")).to_contain_text("5/5")
        sign_out(page)
        sign_in(page, fixture_manager.username, password)
        for route in [
            "/quan-ly/",
            "/quan-ly/ca-lam/",
            "/quan-ly/khach-hang/",
            "/quan-ly/dich-vu/",
            "/quan-ly/chi-nhanh/",
            "/quan-ly/bao-cao/",
        ]:
            response = page.goto(BASE_URL + route)
            assert response.status == 200, (route, response.status)
        with page.expect_download() as download:
            page.get_by_role("link", name="Xuất CSV").click()
        downloaded = download.value
        downloaded.save_as(str(output / "doanh-thu.csv"))
        assert (output / "doanh-thu.csv").stat().st_size > 100
        page.goto(BASE_URL + "/quan-ly/")
        page.screenshot(path=str(screenshots / "dashboard-desktop.png"), full_page=True)
        for width in [390, 768]:
            page.set_viewport_size({"width": width, "height": 844})
            for route in ["/", "/dat-lich/", "/quan-ly/", "/quan-ly/bao-cao/"]:
                page.goto(BASE_URL + route)
                actual = page.locator("body").evaluate("(el)=>el.scrollWidth")
                assert actual <= width, (route, width, actual)
            if width == 390:
                page.goto(BASE_URL + "/quan-ly/")
                page.screenshot(path=str(screenshots / "dashboard-mobile.png"), full_page=True)
                page.get_by_role("button", name="Mở menu").click()
                expect(page.locator("#sidebar")).to_have_class(
                    __import__("re").compile(r"\bopen\b")
                )
                page.keyboard.press("Escape")
                expect(page.locator("#sidebar")).not_to_have_class(
                    __import__("re").compile(r"\bopen\b")
                )
        assert not errors, errors
        browser.close()
    print(
        "PASS: registration, booking, cancellation, reception check-in, service, mock payment, invoice, review, CSV, mobile/tablet, menu; no JavaScript errors."
    )
finally:
    Session.objects.filter(session_key__in=session_keys).delete()
    cleanup()
    AuditLog.objects.filter(actor__in=[fixture_reception, fixture_manager]).delete()
    fixture_reception.delete()
    fixture_manager.delete()
    Shift.objects.filter(employee=fixture_employee).delete()
    fixture_employee.delete()
    fixture_chair.delete()
    fixture_branch.delete()
