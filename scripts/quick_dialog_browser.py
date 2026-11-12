"""Browser regressions on an isolated Django test database, never the application data.

BROWSER_EXECUTABLE=/usr/bin/chromium .venv/bin/python scripts/quick_dialog_browser.py
Requires requirements-quality.txt and Playwright's Chromium (or BROWSER_EXECUTABLE).
"""

import os
import sys
import subprocess
import re
from contextlib import contextmanager
from io import BytesIO
from datetime import time, timedelta
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django

django.setup()
from django.conf import settings
from django.db import connection
from django.test import LiveServerTestCase, override_settings
from django.test.runner import DiscoverRunner
from django.urls import reverse
from django.utils import timezone
from playwright.sync_api import sync_playwright, expect
from openpyxl import load_workbook
from salon.models import Service, Appointment
from salon.services import local_at, transition
from salon.features import get_resource, headers
from salon.tests.test_workflows import Fixtures


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class QuickDialogBrowser(Fixtures, LiveServerTestCase):
    def setUp(self):
        self.make_data()
        self.errors = []
        self.use_user(self.manager)

    def use_user(self, user):
        self.client.force_login(user)
        self.cookie = {
            "name": settings.SESSION_COOKIE_NAME,
            "value": self.client.cookies[settings.SESSION_COOKIE_NAME].value,
            "url": self.live_server_url,
        }

    @contextmanager
    def browser_page(self, **options):
        with sync_playwright() as p:
            launch = {"args": ["--no-sandbox", "--disable-dev-shm-usage"]}
            if os.getenv("BROWSER_EXECUTABLE"):
                launch["executable_path"] = os.environ["BROWSER_EXECUTABLE"]
            browser = p.chromium.launch(**launch)
            context = browser.new_context(**options)
            context.add_cookies([self.cookie])
            page = context.new_page()
            page.on("pageerror", lambda error: self.errors.append(str(error).splitlines()[0][:160]))
            try:
                yield page
            except Exception:
                print("Browser script errors:", self.errors)
                print(
                    "Dialog initialized:",
                    page.evaluate("document.body.classList.contains('quick-ready')"),
                )
                raise
            finally:
                browser.close()
        self.assertEqual(self.errors, [])

    def test_list_opens_and_escape_restores_focus(self):
        with self.browser_page(viewport={"width": 1440, "height": 900}) as page:
            location = self.live_server_url + reverse("settings")
            page.goto(location)
            link = page.locator(
                f'a.settings-card[href="{reverse("resource_list", args=["dich-vu"])}"]'
            )
            link.click()
            dialog = page.get_by_role("dialog")
            expect(dialog).to_be_visible()
            expect(dialog.locator("table")).to_be_visible()
            self.assertEqual(page.url, location)
            page.keyboard.press("Escape")
            expect(dialog).not_to_be_visible()
            expect(link).to_be_focused()

    def open_services(self, page):
        page.goto(self.live_server_url + reverse("settings"))
        page.locator(
            f'a.settings-card[href="{reverse("resource_list", args=["dich-vu"])}"]'
        ).click()
        expect(page.get_by_role("dialog").locator("table")).to_be_visible()
        return page.get_by_role("dialog")

    def test_crud_validation_filters_and_downloads_stay_in_dialog(self):
        with self.browser_page(viewport={"width": 1440, "height": 900}) as page:
            dialog = self.open_services(page)
            dialog.get_by_role("link", name="Thêm mới", exact=True).click()
            form = dialog.locator('form:has(input[name="price"])')
            form.locator('[name="name"]').fill("Dịch vụ kiểm tra tại chỗ")
            form.locator('[name="price"]').fill("0")
            form.locator('[name="duration"]').fill("30")
            form.evaluate("form => form.noValidate = true")
            dialog.locator("[data-quick-submit] button").click()
            expect(dialog.locator(".errorlist")).to_be_visible()
            expect(dialog.locator('[name="name"]')).to_have_value("Dịch vụ kiểm tra tại chỗ")
            dialog.locator('[name="price"]').fill("120000")
            dialog.locator("[data-quick-submit] button").click()
            row = dialog.locator("tr", has_text="Dịch vụ kiểm tra tại chỗ")
            expect(row).to_be_visible()
            row.get_by_role("link", name="Sửa", exact=True).click()
            dialog.locator('[name="name"]').fill("Dịch vụ đã cập nhật")
            dialog.locator("[data-quick-submit] button").click()
            expect(dialog.locator("tr", has_text="Dịch vụ đã cập nhật")).to_be_visible()
            search = dialog.locator('form[method="get"]')
            search.locator('[name="q"]').fill("đã cập nhật")
            search.get_by_role("button", name="Tìm kiếm").click()
            expect(dialog.locator("tbody tr")).to_have_count(1)
            for label, suffix in [("Xuất Excel", ".xlsx"), ("Xuất PDF", ".pdf")]:
                with page.expect_download() as download:
                    dialog.get_by_role("link", name=label, exact=True).click()
                self.assertTrue(download.value.suggested_filename.endswith(suffix))
                expect(dialog).to_be_visible()
            row = dialog.locator("tr", has_text="Dịch vụ đã cập nhật")
            row.get_by_role("link", name="Xóa", exact=True).click()
            dialog.locator('[name="confirm"]').check()
            dialog.locator("[data-quick-submit] button").click()
            expect(dialog.locator("table")).to_be_visible()
            expect(dialog.locator("tr", has_text="Dịch vụ đã cập nhật")).to_have_count(0)
        self.assertFalse(Service.objects.filter(name="Dịch vụ đã cập nhật").exists())

    def test_unsaved_form_can_be_kept_and_discarded(self):
        with self.browser_page(viewport={"width": 768, "height": 900}) as page:
            dialog = self.open_services(page)
            dialog.get_by_role("link", name="Thêm mới", exact=True).click()
            dialog.locator('[name="name"]').fill("Chưa lưu")
            page.once("dialog", lambda prompt: prompt.dismiss())
            page.keyboard.press("Escape")
            expect(dialog).to_be_visible()
            expect(dialog.locator('[name="name"]')).to_have_value("Chưa lưu")
            page.once("dialog", lambda prompt: prompt.accept())
            page.keyboard.press("Escape")
            expect(dialog).not_to_be_visible()
        self.assertFalse(Service.objects.filter(name="Chưa lưu").exists())

    def test_get_network_error_retry_and_back(self):
        with self.browser_page() as page:
            page.goto(self.live_server_url + reverse("settings"))
            address = "**" + reverse("resource_list", args=["dich-vu"])
            page.route(address, lambda route: route.abort())
            page.locator(
                f'a.settings-card[href="{reverse("resource_list", args=["dich-vu"])}"]'
            ).click()
            dialog = page.get_by_role("dialog")
            expect(dialog.get_by_role("button", name="Thử lại")).to_be_visible()
            page.unroute(address)
            dialog.get_by_role("button", name="Thử lại").click()
            expect(dialog.locator("table")).to_be_visible()
            dialog.get_by_role("button", name="Đóng cửa sổ").click()
            expect(dialog).not_to_be_visible()

    def test_menu_responsive_keyboard_and_accessibility(self):
        axe = (ROOT / "scripts/browser-audit/node_modules/axe-core/axe.min.js").read_text()
        output = ROOT / "test-results/quick-dialog"
        output.mkdir(parents=True, exist_ok=True)
        with self.browser_page() as page:
            page.goto(self.live_server_url + reverse("settings"))
            for width in [320, 768, 1024, 1440]:
                page.set_viewport_size({"width": width, "height": 900})
                page.get_by_role("button", name="Thao tác nhanh", exact=True).click()
                dialog = page.get_by_role("dialog")
                expect(dialog).to_be_visible()
                box = dialog.bounding_box()
                self.assertGreaterEqual(box["x"], 0)
                self.assertLessEqual(box["x"] + box["width"], width)
                page.keyboard.press("Tab")
                self.assertTrue(dialog.evaluate("el => el.contains(document.activeElement)"))
                page.evaluate(axe)
                violations = page.evaluate("""async () => (await axe.run(document.querySelector('#quick-dialog'))).violations
                    .filter(v => ['critical', 'serious'].includes(v.impact)).map(v => ({id:v.id, nodes:v.nodes.map(n=>({target:n.target, summary:n.failureSummary}))}))""")
                self.assertEqual(violations, [])
                page.screenshot(path=str(output / f"tools-{width}.png"))
                dialog.get_by_role("link", name="Dịch vụ & combo").click()
                dialog.get_by_role("link", name="Thêm mới", exact=True).click()
                expect(dialog.locator("[data-quick-submit] button")).to_be_visible()
                self.assertTrue(
                    dialog.locator("[data-quick-body]").evaluate(
                        "el => el.scrollWidth<=el.clientWidth+1"
                    )
                )
                violations = page.evaluate("""async () => (await axe.run(document.querySelector('#quick-dialog'))).violations
                    .filter(v => ['critical', 'serious'].includes(v.impact)).map(v => v.id)""")
                self.assertEqual(violations, [])
                page.screenshot(path=str(output / f"form-{width}.png"))
                page.keyboard.press("Escape")
                expect(dialog).not_to_be_visible()
            page.emulate_media(reduced_motion="reduce")
            page.get_by_role("button", name="Thao tác nhanh", exact=True).click()
            self.assertEqual(
                page.get_by_role("dialog").evaluate("el => getComputedStyle(el).animationName"),
                "none",
            )

    def test_customer_booking_slots_and_cancel_with_scoped_ids(self):
        self.use_user(self.customer)
        with self.browser_page(viewport={"width": 390, "height": 844}) as page:
            page.goto(self.live_server_url + reverse("profile"))
            page.get_by_role("button", name="Thao tác nhanh", exact=True).click()
            dialog = page.get_by_role("dialog")
            expect(dialog.locator('a[href^="/quan-ly/"]')).to_have_count(0)
            dialog.get_by_role("link", name="Đặt lịch mới").click()
            dialog.locator('[name="branch"]').select_option(str(self.branch.pk))
            dialog.locator(f'[name="services"][value="{self.service.pk}"]').check()
            dialog.locator('[name="employee"]').select_option(str(self.employee.pk))
            dialog.get_by_role("button", name="10:00", exact=True).click()
            button = dialog.locator("[data-quick-submit] button")
            expect(button).to_be_enabled()
            self.assertTrue(
                dialog.locator("[data-quick-body]").evaluate(
                    "el => el.scrollWidth<=el.clientWidth+1"
                )
            )
            output = ROOT / "test-results/quick-dialog"
            output.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(output / "booking-390.png"))
            button.click()
            expect(dialog.locator(".badge.large")).to_have_text("Đã đặt")
            self.assertEqual(page.url, self.live_server_url + reverse("profile"))
            dialog.get_by_role("link", name="Hủy lịch hẹn", exact=True).click()
            dialog.locator('[name="confirm"]').check()
            dialog.locator("[data-quick-submit] button").click()
            expect(dialog.locator(".badge.large")).to_have_text("Đã hủy")
            ids = page.locator("[id]").evaluate_all("nodes => nodes.map(el => el.id)")
            self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(list(Appointment.objects.values_list("status", flat=True)), ["cancelled"])

    def test_excel_upload_preview_and_confirmation(self):
        response = self.client.get(
            reverse("feature_export", args=["dich-vu", "xlsx"]) + "?template=1"
        )
        workbook = load_workbook(BytesIO(response.content))
        sheet = workbook.active
        self.assertEqual([cell.value for cell in sheet[1]], headers(get_resource("dich-vu")))
        sheet.append([None, "Dịch vụ từ file kiểm thử", "", "hair", 150000, 30, True])
        buffer = BytesIO()
        workbook.save(buffer)
        with self.browser_page() as page:
            dialog = self.open_services(page)
            dialog.get_by_role("link", name="Nhập Excel", exact=True).click()
            dialog.locator('[name="file"]').set_input_files(
                {
                    "name": "kiem-thu.xlsx",
                    "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "buffer": buffer.getvalue(),
                }
            )
            dialog.locator("[data-quick-submit] button").click()
            expect(dialog.locator('input[name="token"]')).to_have_count(1)
            expect(dialog.locator("[data-quick-submit] button")).to_have_text(
                "Xác nhận nhập dữ liệu"
            )
            dialog.locator("[data-quick-submit] button").click()
            expect(dialog.locator("tr", has_text="Dịch vụ từ file kiểm thử")).to_be_visible()
        self.assertEqual(Service.objects.filter(name="Dịch vụ từ file kiểm thử").count(), 1)

    def test_links_work_without_javascript(self):
        with self.browser_page(java_script_enabled=False) as page:
            page.goto(self.live_server_url + reverse("settings"))
            page.locator(
                f'a.settings-card[href="{reverse("resource_list", args=["dich-vu"])}"]'
            ).click()
            expect(page.locator("table")).to_be_visible()
            self.assertEqual(
                page.url, self.live_server_url + reverse("resource_list", args=["dich-vu"])
            )
            page.get_by_role("link", name="Thêm mới", exact=True).click()
            expect(page.locator('[name="name"]')).to_be_visible()

    def test_payment_quote_and_confirmation_keep_server_rules(self):
        a = self.reserve()
        a.start_at = local_at(timezone.localdate(), time(10))
        a.end_at = a.start_at + timedelta(minutes=30)
        a.save()
        with patch("salon.services.timezone.now", return_value=a.start_at):
            for action in ["checkin", "start", "finish"]:
                transition(pk=a.pk, actor=self.manager, action=action, chair_id=self.chair.pk)
        with self.browser_page(viewport={"width": 1024, "height": 800}) as page:
            page.goto(self.live_server_url + reverse("settings"))
            page.evaluate(
                "url => {const a=document.createElement('a'); a.href=url; a.textContent='Lịch kiểm tra'; a.id='browser-appointment'; document.querySelector('main').append(a);}",
                reverse("appointment_detail", args=[a.pk]),
            )
            page.locator("#browser-appointment").click()
            dialog = page.get_by_role("dialog")
            button = dialog.locator("[data-quick-submit] button")
            expect(button).to_be_enabled()
            dialog.locator('[name="voucher_code"]').fill("KHONGTONTAI")
            expect(button).to_be_disabled()
            dialog.locator('[name="voucher_code"]').fill("")
            expect(button).to_be_enabled()
            page.once("dialog", lambda prompt: prompt.accept())
            button.click()
            expect(dialog.locator(".badge.large")).to_have_text("Đã thanh toán")
            dialog.get_by_role("link", name="Xem hóa đơn", exact=False).click()
            expect(dialog.locator(".invoice-paper")).to_be_visible()
            page.emulate_media(media="print")
            expect(page.locator("body > .staff-main")).not_to_be_visible()
            expect(dialog.locator(".invoice-paper")).to_be_visible()
            expect(dialog.locator("[data-quick-footer]")).not_to_be_visible()
            page.emulate_media(media="screen")
        a.refresh_from_db()
        self.assertEqual(a.status, "completed")
        self.assertEqual(a.invoice.total, 100000)

    def test_uncertain_post_is_not_replayed_and_duplicates_are_blocked(self):
        with self.browser_page() as page:
            dialog = self.open_services(page)
            dialog.get_by_role("link", name="Thêm mới", exact=True).click()
            dialog.locator('[name="name"]').fill("Gửi đúng một lần")
            dialog.locator('[name="price"]').fill("100000")
            dialog.locator('[name="duration"]').fill("30")
            posts = []

            def lose_reply(route):
                if route.request.method == "POST":
                    posts.append(1)
                    route.fetch()
                    route.abort()
                else:
                    route.continue_()

            page.route("**" + reverse("resource_create", args=["dich-vu"]), lose_reply)
            dialog.locator('form:has(input[name="price"])').evaluate(
                "form => {form.requestSubmit(); form.requestSubmit();}"
            )
            expect(dialog.locator("[data-quick-status]")).to_contain_text(
                "Chưa xác nhận được kết quả"
            )
            self.assertEqual(len(posts), 1)
        self.assertEqual(Service.objects.filter(name="Gửi đúng một lần").count(), 1)

    def test_saving_restores_background_filter_and_scroll(self):
        Service.objects.bulk_create(
            [Service(name=f"Vị trí {i:02}", price=100000, duration=30) for i in range(30)]
        )
        with self.browser_page(viewport={"width": 1440, "height": 700}) as page:
            address = (
                self.live_server_url
                + reverse("resource_list", args=["dich-vu"])
                + "?q=V%E1%BB%8B+tr%C3%AD&per_page=20"
            )
            page.goto(address)
            link = page.locator("tbody tr").last.get_by_role("link", name="Sửa", exact=True)
            link.scroll_into_view_if_needed()
            original_y = page.evaluate("window.scrollY")
            self.assertGreater(original_y, 0)
            link.click()
            dialog = page.get_by_role("dialog")
            dialog.locator('[name="price"]').fill("110000")
            dialog.locator("[data-quick-submit] button").click()
            expect(dialog.locator("table")).to_be_visible()
            dialog.get_by_role("link", name="Tiếp →", exact=True).click()
            expect(dialog.locator(".pagination")).to_contain_text("Trang 2 /")
            with page.expect_navigation(wait_until="load"):
                dialog.get_by_role("button", name="Đóng cửa sổ").click()
            page.wait_for_function("y => Math.abs(window.scrollY-y)<40", arg=original_y)
            self.assertEqual(page.url, address)

    def test_customer_cannot_open_management_even_with_crafted_link(self):
        self.use_user(self.customer)
        with self.browser_page() as page:
            page.goto(self.live_server_url + reverse("profile"))
            page.evaluate(
                "url => {const a=document.createElement('a'); a.href=url; a.id='browser-forbidden'; a.textContent='Kiểm tra quyền'; document.querySelector('main').append(a);}",
                reverse("resource_create", args=["dich-vu"]),
            )
            page.locator("#browser-forbidden").click()
            dialog = page.get_by_role("dialog")
            expect(dialog.get_by_role("heading", name="Khu vực cần phân quyền.")).to_be_visible()
            expect(dialog.locator("form")).to_have_count(0)

    def test_existing_customer_journey_on_isolated_database(self):
        environment = dict(
            os.environ,
            POSTGRES_DB=connection.settings_dict["NAME"],
            DJANGO_DEBUG="1",
            APP_BASE_URL=self.live_server_url,
        )
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/customer_ui_smoke.py")],
            env=environment,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=240,
        )
        if result.returncode:
            lines = re.findall(r'customer_ui_smoke\.py", line (\d+)', result.stderr)
            self.fail("Customer smoke failed at source line(s): " + ", ".join(lines))
        self.assertIn("PASS:", result.stdout)

    def test_profile_sections_switch_footer_and_keep_labels_scoped(self):
        self.use_user(self.customer)
        with self.browser_page(viewport={"width": 768, "height": 844}) as page:
            page.goto(self.live_server_url + reverse("profile"))
            page.get_by_role("button", name="Thao tác nhanh", exact=True).click()
            dialog = page.get_by_role("dialog")
            dialog.get_by_role("link", name="Đổi mật khẩu", exact=False).click()
            expect(dialog.locator("[data-quick-submit] button")).to_have_text("Đổi mật khẩu")
            dialog.locator('a[href$="#quick-content-profile-form"]').click()
            expect(dialog.locator("[data-quick-submit] button")).to_have_text("Lưu thông tin")
            dialog.locator('label[for="quick-content-id_full_name"]').click()
            expect(dialog.locator('[data-quick-id="id_full_name"]')).to_be_focused()
            dialog.locator('a[href$="#quick-content-password-form"]').click()
            expect(dialog.locator("[data-quick-submit] button")).to_have_text("Đổi mật khẩu")
            ids = page.locator("[id]").evaluate_all("nodes => nodes.map(el => el.id)")
            self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
    raise SystemExit(
        DiscoverRunner(verbosity=1, interactive=False).run_tests(
            sys.argv[1:] or ["scripts.quick_dialog_browser.QuickDialogBrowser"]
        )
    )
