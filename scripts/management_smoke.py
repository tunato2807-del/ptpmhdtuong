"""Exercise custom management/profile screens on a local demo; clean own data."""

import os
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django

django.setup()
from django.conf import settings
from django.utils import timezone
from salon.models import User, Branch, Service, Employee, Chair, Shift, AuditLog
from playwright.sync_api import sync_playwright, expect

BASE = os.getenv("APP_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
if not settings.DEBUG or urlsplit(BASE).hostname not in ["127.0.0.1", "localhost"]:
    raise SystemExit("Only run on a local DEBUG demo server using this database.")
marker = "ui-" + uuid.uuid4().hex[:10]
password = "Start@Test2026"
new_password = "Fresh@Test2026"
manager = User.objects.create_user(
    username=marker,
    password=password,
    full_name="Quản trị trình diễn",
    phone="0901234567",
    email=marker + "@example.com",
    role="manager",
)
OUTPUT = ROOT / "docs/screenshots"
OUTPUT.mkdir(exist_ok=True)
errors = []
pool = ThreadPoolExecutor(max_workers=1)


def db(operation):
    # Playwright owns an event loop; perform ORM reads on a separate sync thread.
    def execute():
        from django.db import connections

        try:
            return operation()
        finally:
            connections.close_all()

    return pool.submit(execute).result()


def clean():
    AuditLog.objects.filter(actor__username__startswith=marker).delete()
    Shift.objects.filter(employee__name=marker).delete()
    User.objects.filter(username=marker + "-reception").delete()
    Chair.objects.filter(branch__name=marker).delete()
    Employee.objects.filter(name=marker).delete()
    Branch.objects.filter(name=marker).delete()
    Service.objects.filter(name=marker).delete()
    User.objects.filter(username=marker).delete()


def login(page, username, pw):
    page.goto(BASE + "/dang-nhap/")
    page.locator("#id_username").fill(username)
    page.locator("#id_password").fill(pw)
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_url("**/quan-ly/")


def create(page, resource, values):
    page.goto(BASE + "/quan-ly/thiet-lap/" + resource + "/them/")
    for key, value in values.items():
        field = page.locator("#id_" + key)
        if field.evaluate("(el)=>el.tagName") == "SELECT":
            field.select_option(str(value))
        elif key in ["active", "is_active"]:
            field.set_checked(bool(value))
        else:
            field.fill(str(value))
    page.get_by_role("button", name="Tạo mới", exact=True).click()
    page.wait_for_url("**/quan-ly/thiet-lap/" + resource + "/")
    expect(page.locator(".messages")).to_contain_text("Đã lưu")


try:
    with sync_playwright() as p:
        options = {"headless": True, "args": ["--no-sandbox", "--disable-dev-shm-usage"]}
        if os.getenv("BROWSER_EXECUTABLE"):
            options["executable_path"] = os.environ["BROWSER_EXECUTABLE"]
        browser = p.chromium.launch(**options)
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, locale="vi-VN")
        page.on("pageerror", lambda error: errors.append(str(error)))
        login(page, marker, password)
        page.goto(BASE + "/quan-ly/thiet-lap/")
        expect(page.locator(".settings-card")).to_have_count(6)
        assert page.locator('a[href^="/admin/"]').count() == 0
        page.screenshot(path=str(OUTPUT / "management-desktop.png"), full_page=True)
        create(
            page,
            "chi-nhanh",
            {
                "name": marker,
                "address": "TP. Hồ Chí Minh",
                "phone": "0901111222",
                "opens_at": "09:00",
                "closes_at": "21:00",
                "active": True,
            },
        )
        branch = db(lambda: Branch.objects.get(name=marker))
        create(
            page,
            "stylist",
            {
                "name": marker,
                "branch": branch.pk,
                "specialty": "Fade & tạo kiểu",
                "bio": "Chăm chút từng đường kéo",
                "active": True,
            },
        )
        employee = db(lambda: Employee.objects.get(name=marker))
        create(page, "ghe", {"name": "Ghế UI", "branch": branch.pk, "active": True})
        create(
            page,
            "dich-vu",
            {
                "name": marker,
                "description": "Dịch vụ kiểm thử tự dọn dữ liệu.",
                "kind": "hair",
                "price": 120000,
                "duration": 30,
                "active": True,
            },
        )
        service = db(lambda: Service.objects.get(name=marker))
        tomorrow = timezone.localdate() + timedelta(days=1)
        create(
            page,
            "ca-lam",
            {
                "employee": employee.pk,
                "start_at": str(tomorrow) + "T09:00",
                "end_at": str(tomorrow) + "T17:00",
            },
        )
        create(
            page,
            "tai-khoan",
            {
                "username": marker + "-reception",
                "full_name": "Lễ tân kiểm thử",
                "email": marker + "-r@example.com",
                "role": "receptionist",
                "branch": branch.pk,
                "is_active": True,
                "new_password": "Reception@Test2026",
            },
        )
        page.goto(BASE + f"/quan-ly/thiet-lap/dich-vu/{service.pk}/sua/")
        page.locator("#id_price").fill("150000")
        page.get_by_role("button", name="Lưu thay đổi").click()
        page.wait_for_url("**/quan-ly/thiet-lap/dich-vu/")
        expect(page.locator("tbody tr").first).to_contain_text("150.000 ₫")
        page.goto(BASE + "/tai-khoan/")
        page.locator("#id_full_name").fill("Quản trị đã cập nhật")
        page.get_by_role("button", name="Lưu thông tin").click()
        expect(page.locator(".profile-identity")).to_contain_text("Quản trị đã cập nhật")
        page.locator("#id_old_password").fill("wrong-password")
        page.locator("#id_new_password1").fill(new_password)
        page.locator("#id_new_password2").fill(new_password)
        page.get_by_role("button", name="Đổi mật khẩu", exact=True).click()
        expect(page.locator("#password-form .errorlist")).to_be_visible()
        page.locator("#id_old_password").fill(password)
        page.locator("#id_new_password1").fill(new_password)
        page.locator("#id_new_password2").fill(new_password)
        page.get_by_role("button", name="Đổi mật khẩu", exact=True).click()
        expect(page.locator(".messages")).to_contain_text("Đã đổi mật khẩu")
        page.screenshot(path=str(OUTPUT / "profile-desktop.png"), full_page=True)
        # All six delete screens are real POST forms with an explicit confirmation.
        objects = [
            ("ca-lam", db(lambda: Shift.objects.get(employee=employee))),
            ("ghe", db(lambda: Chair.objects.get(branch=branch))),
            ("stylist", employee),
            ("dich-vu", service),
            ("tai-khoan", db(lambda: User.objects.get(username=marker + "-reception"))),
            ("chi-nhanh", branch),
        ]
        for key, obj in objects:
            page.goto(BASE + f"/quan-ly/thiet-lap/{key}/{obj.pk}/xoa/")
            page.locator("#id_confirm").check()
            page.get_by_role("button", name="Xác nhận xóa", exact=True).click()
            page.wait_for_url("**/quan-ly/thiet-lap/" + key + "/")
            assert not db(lambda: type(obj).objects.filter(pk=obj.pk).exists())
        page.goto(BASE + "/quan-ly/thiet-lap/dich-vu/")
        page.screenshot(path=str(OUTPUT / "management-services.png"), full_page=True)
        service = db(lambda: Service.objects.first())
        for width in [320, 390, 768, 1440]:
            page.set_viewport_size({"width": width, "height": 844})
            for route in [
                "/quan-ly/thiet-lap/",
                "/quan-ly/thiet-lap/tai-khoan/",
                f"/quan-ly/thiet-lap/dich-vu/{service.pk}/sua/",
                f"/quan-ly/thiet-lap/dich-vu/{service.pk}/xoa/",
                "/tai-khoan/",
            ]:
                page.goto(BASE + route)
                assert page.locator("body").evaluate("(el)=>el.scrollWidth") <= width, (
                    route,
                    width,
                )
            if width == 390:
                page.screenshot(path=str(OUTPUT / "profile-mobile.png"), full_page=True)
                page.goto(BASE + "/quan-ly/thiet-lap/")
                page.screenshot(path=str(OUTPUT / "management-mobile.png"), full_page=True)
        page.goto(BASE + "/")
        page.get_by_role("button", name="Đăng xuất", exact=True).click()
        login(page, marker, new_password)
        assert page.goto(BASE + "/admin/").status == 404
        assert not errors, errors
        browser.close()
    print(
        "PASS: custom manager without Django staff flags; create all 6 resources, edit price, delete all 6, edit own profile, reject wrong password, change password and sign in again, manager/profile layouts 320–1440px, no Django Admin links or JavaScript errors. Own test data cleaned."
    )
finally:
    pool.shutdown()
    clean()
