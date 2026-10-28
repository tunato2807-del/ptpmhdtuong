"""Blue Edition customer journey on a local demo; no booking/business writes.

Creates a temporary customer, tests real login, then removes its sessions/account.
BROWSER_EXECUTABLE=/usr/bin/chromium .venv/bin/python scripts/customer_ui_smoke.py
"""

import os
import re
import sys
import uuid
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django

django.setup()
from django.conf import settings
from django.contrib.sessions.models import Session
from salon.models import User
from playwright.sync_api import sync_playwright, expect

BASE_URL = os.getenv("APP_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
if not settings.DEBUG or urlsplit(BASE_URL).hostname not in ("127.0.0.1", "localhost"):
    raise SystemExit("Requires a local DEBUG demo using this checkout/database.")
OUTPUT = ROOT / "test-results/blue"
OUTPUT.mkdir(exist_ok=True, parents=True)
username = "blue-customer-" + uuid.uuid4().hex[:12]
password = "Browser@" + uuid.uuid4().hex
user = User.objects.create_user(username=username, password=password, full_name="Khách trải nghiệm")
session_keys = set()
errors, external = [], []


def capture(page, name):
    page.evaluate("document.fonts.ready")
    page.evaluate('document.documentElement.style.scrollBehavior = "auto"')
    height = page.locator("body").evaluate("el => el.scrollHeight")
    for y in range(0, height, 650):
        page.evaluate("y => window.scrollTo(0, y)", y)
        page.wait_for_timeout(60)
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(750)
    assert page.locator("img").evaluate_all(
        "images => images.every(i => i.complete && i.naturalWidth > 0)"
    ), "An image failed to load"
    page.screenshot(path=str(OUTPUT / name), full_page=True)


try:
    with sync_playwright() as p:
        options = {"headless": True, "args": ["--no-sandbox", "--disable-dev-shm-usage"]}
        if os.getenv("BROWSER_EXECUTABLE"):
            options["executable_path"] = os.environ["BROWSER_EXECUTABLE"]
        browser = p.chromium.launch(**options)
        context = browser.new_context(viewport={"width": 1440, "height": 1000}, locale="vi-VN")
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(type(error).__name__))
        page.on(
            "request",
            lambda req: (
                external.append(urlsplit(req.url).hostname)
                if urlsplit(req.url).hostname != urlsplit(BASE_URL).hostname
                else None
            ),
        )
        page.goto(BASE_URL + "/")
        service_links = page.locator(".be-service-menu > a")
        service_count = service_links.count()
        assert service_count > 0
        slideshow = page.locator("[data-slideshow]")
        slideshow.scroll_into_view_if_needed()
        page.mouse.move(0, 0)
        initial = page.locator(".hero-slide.is-active").get_attribute("alt")
        expect(page.locator(".hero-slide.is-active")).not_to_have_attribute(
            "alt", initial, timeout=9000
        )
        page.get_by_role("button", name="Dừng tự chuyển", exact=True).click()
        expect(page.get_by_role("button", name="Bật tự chuyển", exact=True)).to_be_visible()
        initial = page.locator(".hero-slide.is-active").get_attribute("alt")
        page.get_by_role("button", name="Ảnh tiếp theo", exact=True).click()
        expect(page.locator(".hero-slide.is-active")).not_to_have_attribute("alt", initial)
        capture(page, "home-1440.png")
        # Service selection must survive the anonymous-to-authenticated redirect.
        service_id = parse_qs(urlsplit(service_links.first.get_attribute("href")).query)["service"][
            0
        ]
        service_links.first.click()
        expect(page).to_have_url(re.compile(r"/dang-nhap/\?next="))
        page.locator("#id_username").fill(username)
        page.locator("#id_password").fill(password)
        page.get_by_role("button", name="Đăng nhập", exact=True).click()
        page.wait_for_url("**/dat-lich/?service=*")
        session_keys.update(
            c["value"] for c in context.cookies() if c["name"] == settings.SESSION_COOKIE_NAME
        )
        expect(page.locator(f'input[name="services"][value="{service_id}"]')).to_be_checked()
        page.goto(BASE_URL + "/")
        stylist_link = page.locator(".be-stylist-list > a").first
        values = parse_qs(urlsplit(stylist_link.get_attribute("href")).query)
        stylist_link.click()
        expect(page.locator("#id_branch")).to_have_value(values["branch"][0])
        expect(page.locator("#id_employee")).to_have_value(values["employee"][0])
        expect(page.locator(".mobile-booking")).to_have_count(0)
        page.goto(BASE_URL + "/")
        page.locator("#quick-branch").select_option(index=1)
        selected_branch = page.locator("#quick-branch").input_value()
        page.get_by_role("button", name="Chọn lịch của bạn").click()
        expect(page.locator("#id_branch")).to_have_value(selected_branch)
        page.locator('input[name="services"]').first.check()
        page.locator("#id_employee").select_option(index=1)
        slot = page.locator(".slot-button").first
        expect(slot).to_be_visible()
        chosen_time = slot.inner_text()
        slot.click()
        expect(page.locator("#summary-time")).to_have_text(chosen_time)
        expect(page.locator("#submit-booking")).to_be_enabled()
        expect(page.locator("#summary-branch")).to_have_text(
            page.locator("#id_branch option:checked").inner_text()
        )
        assert page.locator("#summary-total").inner_text() != "0 ₫"
        capture(page, "booking-1440.png")
        # Changing duration invalidates the previous slot immediately, including the ticket.
        page.locator('input[name="services"]').nth(1).check()
        expect(page.locator("#summary-time")).to_have_text("—")
        expect(page.locator("#submit-booking")).to_be_disabled()
        expect(page.locator(".slot-button").first).to_be_visible()
        for width in (320, 390, 768, 1024, 1200, 1440):
            page.set_viewport_size({"width": width, "height": 844})
            for route in ("/", "/dat-lich/", "/tai-khoan/", "/lich-cua-toi/"):
                page.goto(BASE_URL + route)
                assert page.locator("html").evaluate("el => el.scrollWidth") <= width, (
                    route,
                    width,
                )
                expect(page.get_by_role("button", name="Đăng xuất", exact=True)).to_be_visible()
            if width == 390:
                page.goto(BASE_URL + "/")
                menu = page.get_by_role("button", name="Mở điều hướng")
                menu.click()
                expect(page.locator("#customer-nav")).to_be_visible()
                page.keyboard.press("Escape")
                expect(page.locator("#customer-nav")).to_be_hidden()
                expect(menu).to_be_focused()
                capture(page, "home-390.png")
                page.goto(BASE_URL + "/dat-lich/")
                capture(page, "booking-390.png")
                page.goto(BASE_URL + "/tai-khoan/")
                capture(page, "account-390.png")
        page.goto(BASE_URL + "/tai-khoan/")
        capture(page, "account-1440.png")
        page.goto(BASE_URL + "/")
        page.emulate_media(reduced_motion="reduce")
        expect(page.locator("[data-slide-toggle]")).to_be_disabled()
        assert page.locator(".hero-slide").evaluate_all(
            "els => els.every(el => getComputedStyle(el).animationName === 'none')"
        )
        assert page.locator("[data-reveal]").evaluate_all(
            "els => els.every(el => getComputedStyle(el).opacity === '1')"
        )
        page.get_by_role("button", name="Đăng xuất", exact=True).click()
        page.wait_for_url(BASE_URL + "/")
        page.goto(BASE_URL + "/tai-khoan/")
        expect(page).to_have_url(re.compile(r"/dang-nhap/"))
        context.close()
        no_js = browser.new_context(
            java_script_enabled=False, viewport={"width": 390, "height": 844}
        )
        page = no_js.new_page()
        page.goto(BASE_URL + "/")
        expect(page.locator("#customer-nav")).to_be_visible()
        expect(page.locator(".be-service-menu > a:visible")).to_have_count(service_count)
        assert page.locator("[data-reveal]").evaluate_all(
            "els => els.every(el => getComputedStyle(el).opacity === '1')"
        )
        for route in ("/", "/dang-nhap/", "/dang-ky/"):
            page.goto(BASE_URL + route)
            assert page.locator("html").evaluate("el => el.scrollWidth") <= 390
        no_js.close()
        browser.close()
    assert not errors, errors
    assert not external, external
    print(
        "PASS: real login/logout, service/stylist/branch preselection, slots and live ticket reset, slideshow controls/autoplay, 24 responsive views, mobile menu/Escape, photos, reduced motion, no-JS navigation; no JS errors/external requests."
    )
finally:
    Session.objects.filter(session_key__in=session_keys).delete()
    User.objects.filter(pk=user.pk, username=username).delete()
