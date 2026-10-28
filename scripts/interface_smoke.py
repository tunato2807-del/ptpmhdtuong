"""Check real layouts, assets and logout on the local demo, without business writes.

.venv/bin/python scripts/interface_smoke.py
Optional BROWSER_EXECUTABLE, APP_BASE_URL, UI_SMOKE_SCREENSHOTS=1.
Uses temporary sessions for existing demo roles; removes them on completion.
"""

import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django

django.setup()
from django.conf import settings
from django.contrib.sessions.models import Session
from django.test import Client
from salon.models import User, Service, Appointment
from playwright.sync_api import sync_playwright, expect

BASE = os.getenv("APP_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
if not settings.DEBUG or urlsplit(BASE).hostname not in ("127.0.0.1", "localhost"):
    raise SystemExit("Run only on a local DEBUG demo using this checkout/database.")
WIDTHS = (320, 390, 768, 1024, 1440, 1920)
SESSIONS = {}
ROUTES = {"anonymous": ["/", "/dang-nhap/", "/dang-ky/", "/tim-kiem/", "/quen-mat-khau/"]}
for role in ("customer", "receptionist", "manager"):
    user = User.objects.filter(role=role, is_active=True).first()
    if not user:
        raise SystemExit("Missing demo role: " + role)
    client = Client()
    client.force_login(user)
    SESSIONS[role] = client.session.session_key
    ROUTES[role] = [
        "/",
        "/tai-khoan/",
        "/dat-lich/",
        "/lich-cua-toi/",
        "/thong-bao/",
        "/diem-tich-luy/",
    ]
    if user.is_operator:
        ROUTES[role] += [
            "/quan-ly/",
            "/quan-ly/khach-hang/",
            "/quan-ly/dich-vu/",
            "/quan-ly/chi-nhanh/",
            "/quan-ly/ca-lam/",
            "/quan-ly/bao-cao/",
            "/quan-ly/lich-tuan/",
            "/quan-ly/hieu-qua/",
        ]
    if user.is_manager:
        ROUTES[role] += ["/quan-ly/thiet-lap/", "/quan-ly/nhat-ky/"]
        for key in ("dich-vu", "chi-nhanh", "stylist", "ghe", "ca-lam", "tai-khoan"):
            ROUTES[role] += [f"/quan-ly/thiet-lap/{key}/", f"/quan-ly/thiet-lap/{key}/them/"]
        service = Service.objects.first()
        for action in ("", "sua/", "xoa/"):
            ROUTES[role].append(f"/quan-ly/thiet-lap/dich-vu/{service.pk}/" + action)
    appt = Appointment.objects.filter(customer=user).first()
    if appt:
        ROUTES[role].append(f"/lich-hen/{appt.pk}/")

errors = []
count = 0
output = ROOT / "test-results/interface"
output.mkdir(parents=True, exist_ok=True)
try:
    with sync_playwright() as playwright:
        options = {"headless": True, "args": ["--no-sandbox", "--disable-dev-shm-usage"]}
        if os.getenv("BROWSER_EXECUTABLE"):
            options["executable_path"] = os.environ["BROWSER_EXECUTABLE"]
        browser = playwright.chromium.launch(**options)
        for role, routes in ROUTES.items():
            context = browser.new_context(locale="vi-VN")
            if role in SESSIONS:
                context.add_cookies(
                    [{"name": settings.SESSION_COOKIE_NAME, "value": SESSIONS[role], "url": BASE}]
                )
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on(
                "response",
                lambda response: (
                    errors.append(f"{response.status}: {response.url}")
                    if response.status >= 400
                    else None
                ),
            )
            for width in WIDTHS:
                page.set_viewport_size({"width": width, "height": 900})
                for path in routes:
                    response = page.goto(BASE + path)
                    assert response.status == 200, (role, path, response.status)
                    page.evaluate("document.fonts.ready")
                    expect(page.locator("main")).to_be_visible()
                    assert page.locator("html").evaluate("(el)=>el.scrollWidth") <= width, (
                        role,
                        path,
                        width,
                        "overflow",
                    )
                    for css in ("app", "customer", "management", "typography"):
                        assert page.locator(f'link[href*="css/{css}."]').count() == 1, (path, css)
                    icons = page.locator("svg.ui-icon").evaluate_all(
                        "(els)=>els.map(el=>({w:el.getBoundingClientRect().width,h:el.getBoundingClientRect().height}))"
                    )
                    assert all(icon["w"] <= 32 and icon["h"] <= 32 for icon in icons), (
                        path,
                        width,
                        icons,
                    )
                    if role != "anonymous":
                        expect(
                            page.get_by_role("button", name="Đăng xuất", exact=True)
                        ).to_be_visible()
                    if path == "/quan-ly/thiet-lap/":
                        expect(page.locator(".settings-card")).to_have_count(6)
                        columns = page.locator(".settings-grid").evaluate(
                            '(el)=>getComputedStyle(el).gridTemplateColumns.split(" ").length'
                        )
                        assert columns == (3 if width > 1100 else 2 if width > 390 else 1), (
                            width,
                            columns,
                        )
                    if path == "/tai-khoan/":
                        columns = page.locator(".profile-layout").evaluate(
                            '(el)=>getComputedStyle(el).gridTemplateColumns.split(" ").length'
                        )
                        assert columns == (2 if width > 760 else 1), (width, columns)
                    if (
                        os.getenv("UI_SMOKE_SCREENSHOTS") == "1"
                        and role == "manager"
                        and path in ("/quan-ly/thiet-lap/", "/tai-khoan/")
                        and width in (390, 1440)
                    ):
                        filename = path.strip("/").replace("/", "-")
                        page.screenshot(
                            path=str(output / f"{filename}-{width}.png"), full_page=True
                        )
                    count += 1
            if role != "anonymous":
                for width in (390, 1440):
                    # Use a fresh context with the same session only until logout.
                    page.set_viewport_size({"width": width, "height": 900})
                    page.goto(BASE + ("/quan-ly/" if role != "customer" else "/"))
                    page.get_by_role("button", name="Đăng xuất", exact=True).click()
                    page.wait_for_url(BASE + "/")
                    page.goto(BASE + "/tai-khoan/")
                    assert urlsplit(page.url).path == "/dang-nhap/", (role, "session not ended")
                    # A single POST invalidates the session; verify only once per role.
                    break
            context.close()
        browser.close()
    assert not errors, errors
    print(
        f"PASS: {count} route/viewport checks, 6 widths, assets, bounded icons, settings/profile columns, visible POST logout for all roles; no browser or asset errors."
    )
finally:
    Session.objects.filter(session_key__in=SESSIONS.values()).delete()
