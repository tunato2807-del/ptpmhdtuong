"""Local isolated axe/CDP audit. No personal browser or external requests.

Install dev Python requirements and `npm ci --ignore-scripts --prefix scripts/browser-audit`.
Run with BROWSER_EXECUTABLE=/path/to/chromium; optional --output path.
"""

import argparse
import json
import os
import sys
import uuid
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django

django.setup()
from django.conf import settings
from django.test import Client
from salon.models import User
from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "test-results/quality-browser.json")
    args = parser.parse_args()
    base = os.getenv("APP_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    if not settings.DEBUG or urlsplit(base).hostname not in ("127.0.0.1", "localhost"):
        raise SystemExit("Requires a local DEBUG demo using this database.")
    axe = Path(
        os.getenv("AXE_PATH", str(ROOT / "scripts/browser-audit/node_modules/axe-core/axe.min.js"))
    ).read_text()
    users = []
    sessions = {}
    report = {"tool": "Playwright/Chromium CDP + axe-core", "pages": [], "lab_home": []}
    try:
        for role in ("manager", "customer"):
            user = User.objects.create_user(
                username="quality-" + uuid.uuid4().hex, role=role, full_name="Tài khoản kiểm thử"
            )
            users.append(user)
            client = Client()
            client.force_login(user)
            sessions[role] = client.cookies[settings.SESSION_COOKIE_NAME].value
        with sync_playwright() as p:
            options = {"headless": True, "args": ["--no-sandbox", "--disable-dev-shm-usage"]}
            if os.getenv("BROWSER_EXECUTABLE"):
                options["executable_path"] = os.environ["BROWSER_EXECUTABLE"]
            browser = p.chromium.launch(**options)
            cases = {
                "anonymous": ["/", "/dang-nhap/", "/dang-ky/", "/quen-mat-khau/"],
                "customer": ["/tai-khoan/", "/dat-lich/", "/lich-cua-toi/"],
                "manager": [
                    "/quan-ly/",
                    "/quan-ly/van-hanh/",
                    "/quan-ly/tai-nguyen/stylist/",
                    "/quan-ly/thiet-lap/",
                ],
            }
            for width, height in ((1440, 1000), (390, 844)):
                for role, paths in cases.items():
                    context = browser.new_context(
                        viewport={"width": width, "height": height},
                        locale="vi-VN",
                        reduced_motion="reduce",
                    )
                    context.route(
                        "**/*",
                        lambda route: (
                            route.continue_()
                            if urlsplit(route.request.url).hostname == urlsplit(base).hostname
                            else route.abort()
                        ),
                    )
                    if role in sessions:
                        context.add_cookies(
                            [
                                {
                                    "name": settings.SESSION_COOKIE_NAME,
                                    "value": sessions[role],
                                    "url": base,
                                }
                            ]
                        )
                    page = context.new_page()
                    errors = []
                    page.on("pageerror", lambda error: errors.append(type(error).__name__))
                    for path in paths:
                        errors.clear()
                        response = page.goto(base + path)
                        page.evaluate("document.fonts.ready")
                        page.wait_for_timeout(150)
                        page.evaluate(axe)
                        audit = page.evaluate(
                            """async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}});return {violations:r.violations.map(v=>({id:v.id,impact:v.impact,targets:v.nodes.map(n=>n.target)})),passes:r.passes.length}}"""
                        )
                        report["pages"].append(
                            {
                                "role": role,
                                "path": path,
                                "width": width,
                                "status": response.status,
                                "js_errors": list(errors),
                                "overflow": page.evaluate(
                                    "document.documentElement.scrollWidth>innerWidth+1"
                                ),
                                **audit,
                            }
                        )
                    context.close()
            for _ in range(3):
                context = browser.new_context(
                    viewport={"width": 390, "height": 844}, reduced_motion="reduce"
                )
                context.route(
                    "**/*",
                    lambda route: (
                        route.continue_()
                        if urlsplit(route.request.url).hostname == urlsplit(base).hostname
                        else route.abort()
                    ),
                )
                page = context.new_page()
                cdp = context.new_cdp_session(page)
                cdp.send("Network.enable")
                cdp.send("Network.setCacheDisabled", {"cacheDisabled": True})
                cdp.send(
                    "Network.emulateNetworkConditions",
                    {
                        "offline": False,
                        "latency": 150,
                        "downloadThroughput": 200000,
                        "uploadThroughput": 93750,
                    },
                )
                cdp.send("Emulation.setCPUThrottlingRate", {"rate": 4})
                page.add_init_script(
                    """window.lab={lcp:0,cls:0};new PerformanceObserver(l=>{for(const e of l.getEntries())lab.lcp=e.startTime}).observe({type:'largest-contentful-paint',buffered:true});new PerformanceObserver(l=>{for(const e of l.getEntries())if(!e.hadRecentInput)lab.cls+=e.value}).observe({type:'layout-shift',buffered:true});"""
                )
                page.goto(base + "/")
                page.evaluate("document.fonts.ready")
                page.wait_for_timeout(1500)
                report["lab_home"].append(
                    page.evaluate(
                        "({...lab,load:performance.getEntriesByType('navigation')[0].loadEventEnd})"
                    )
                )
                context.close()
            report["browser"] = browser.version
            browser.close()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        bad = [
            r
            for r in report["pages"]
            if r["status"] != 200 or r["js_errors"] or r["overflow"] or r["violations"]
        ]
        print(
            f"Audit: {len(report['pages'])} page/viewport checks; {len(bad)} with issues. {args.output}"
        )
        return bool(bad)
    finally:
        from django.contrib.sessions.models import Session

        Session.objects.filter(session_key__in=sessions.values()).delete()
        for user in users:
            User.objects.filter(pk=user.pk, username=user.username).delete()


if __name__ == "__main__":
    sys.exit(main())
