"""Exercise the customer redesign on a local demo instance; creates no records.
Usage: BROWSER_EXECUTABLE=/tmp/chromium .venv/bin/python scripts/customer_ui_smoke.py
"""
import os
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parent.parent
BASE_URL = os.getenv('APP_BASE_URL', 'http://127.0.0.1:8000').rstrip('/')
if urlsplit(BASE_URL).hostname not in ('127.0.0.1', 'localhost'):
    raise SystemExit('Use this smoke check against a local demo server only.')
OUTPUT = ROOT / 'docs/screenshots'
OUTPUT.mkdir(exist_ok=True)

def capture(page, name, full=True):
    page.evaluate('document.fonts.ready')
    # Scroll through the actual page so lazy photos and reveal animations render.
    page.evaluate('document.documentElement.style.scrollBehavior = "auto"')
    height = page.locator('body').evaluate('(el) => el.scrollHeight')
    for y in range(0, height, 650):
        page.evaluate('(y) => window.scrollTo(0, y)', y)
        page.wait_for_timeout(80)
    page.evaluate('window.scrollTo(0, 0)')
    page.wait_for_timeout(750)
    assert page.locator('img').evaluate_all('(images) => images.every(i => i.complete && i.naturalWidth > 0)')
    page.screenshot(path=str(OUTPUT / name), full_page=full)

with sync_playwright() as p:
    options = {'headless': True, 'args': ['--no-sandbox', '--disable-dev-shm-usage']}
    if os.getenv('BROWSER_EXECUTABLE'): options['executable_path'] = os.environ['BROWSER_EXECUTABLE']
    browser = p.chromium.launch(**options)
    context = browser.new_context(viewport={'width':1440,'height':1000}, locale='vi-VN')
    page = context.new_page()
    errors, external = [], []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('request', lambda request: external.append(request.url) if urlsplit(request.url).hostname not in ('127.0.0.1', 'localhost') else None)
    page.goto(BASE_URL+'/')
    cards = page.locator('.gh-service')
    all_count = cards.count()
    assert all_count > 0
    for kind in ['hair','care','combo','all']:
        button = page.locator(f'[data-service-filter="{kind}"]')
        button.click()
        expect(button).to_have_attribute('aria-pressed','true')
        expected = all_count if kind == 'all' else page.locator(f'.gh-service[data-kind="{kind}"]').count()
        expect(page.locator('.gh-service:visible')).to_have_count(expected)
    gallery = page.locator('#style-gallery')
    gallery.scroll_into_view_if_needed()
    page.get_by_role('button',name='Xem ảnh tiếp theo').click()
    page.wait_for_function('document.querySelector("#style-gallery").scrollLeft > 100')
    page.get_by_role('button',name='Xem ảnh trước').click()
    page.wait_for_function('document.querySelector("#style-gallery").scrollLeft < 2')
    capture(page,'home-desktop.png')
    page.screenshot(path=str(OUTPUT/'home-desktop-top.png'))
    # A selected service survives the authentication redirect.
    service_link = page.locator('.service-price > a').first
    service_id = service_link.get_attribute('href').split('service=')[1]
    service_link.click()
    expect(page).to_have_url(__import__('re').compile(r'/dang-nhap/\?next='))
    page.locator('#id_username').fill('khachhang')
    page.locator('#id_password').fill('Gentleman@2026')
    page.get_by_role('button',name='Đăng nhập').click()
    page.wait_for_url('**/dat-lich/?service=*')
    expect(page.locator(f'input[name="services"][value="{service_id}"]')).to_be_checked()
    page.goto(BASE_URL+'/')
    # Stylist links select both their branch and employee.
    stylist_link = page.locator('.team-member').first
    from urllib.parse import parse_qs
    values = parse_qs(urlsplit(stylist_link.get_attribute('href')).query)
    stylist_link.click()
    expect(page.locator('#id_branch')).to_have_value(values['branch'][0])
    expect(page.locator('#id_employee')).to_have_value(values['employee'][0])
    expect(page.locator('.mobile-booking')).to_have_count(0)
    # Quick booking preserves the branch.
    page.goto(BASE_URL+'/')
    page.locator('#quick-branch').select_option(index=1)
    selected_branch = page.locator('#quick-branch').input_value()
    page.get_by_role('button',name='Tìm lịch trống').click()
    expect(page.locator('#id_branch')).to_have_value(selected_branch)
    page.locator('input[name="services"]').first.check()
    page.locator('#id_employee').select_option(index=1)
    expect(page.locator('.slot-button').first).to_be_visible()
    page.locator('.slot-button').first.click()
    expect(page.locator('#submit-booking')).to_be_enabled()
    capture(page,'booking-desktop.png')
    for width in [320,360,390,768,1024,1440]:
        page.set_viewport_size({'width':width,'height':844})
        for route in ['/','/dat-lich/','/lich-cua-toi/']:
            page.goto(BASE_URL+route)
            actual = page.locator('body').evaluate('(el) => el.scrollWidth')
            assert actual <= width, (route, width, actual)
        if width == 390:
            page.goto(BASE_URL+'/')
            menu = page.get_by_role('button',name='Mở điều hướng')
            menu.click()
            expect(page.locator('#customer-nav')).to_be_visible()
            page.keyboard.press('Escape')
            expect(page.locator('#customer-nav')).to_be_hidden()
            expect(menu).to_be_focused()
            menu.click()
            page.locator('#customer-nav a').first.click()
            expect(page.locator('#customer-nav')).to_be_hidden()
            capture(page,'home-mobile.png')
            page.screenshot(path=str(OUTPUT/'home-mobile-top.png'))
            page.goto(BASE_URL+'/dat-lich/')
            capture(page,'booking-mobile.png')
    # Reduced motion also takes effect when toggled during the session.
    page.goto(BASE_URL+'/')
    page.emulate_media(reduced_motion='reduce')
    assert page.locator('.gh-hero-photo').evaluate('(el) => getComputedStyle(el).animationName') == 'none'
    assert page.locator('[data-reveal]').evaluate_all('(items) => items.every(el => getComputedStyle(el).opacity === "1")')
    assert not errors, errors
    assert not external, external
    context.close()
    no_js = browser.new_context(java_script_enabled=False, viewport={'width':390,'height':844})
    page = no_js.new_page()
    page.goto(BASE_URL+'/')
    expect(page.locator('#customer-nav')).to_be_visible()
    expect(page.locator('.gh-service:visible')).to_have_count(all_count)
    expect(page.locator('.service-filters')).to_be_hidden()
    assert page.locator('[data-reveal]').evaluate_all('(items) => items.every(el => getComputedStyle(el).opacity === "1")')
    for route in ['/dang-nhap/','/dang-ky/']:
        page.goto(BASE_URL+route)
        assert page.locator('body').evaluate('(el)=>el.scrollWidth') <= 390
    no_js.close()
    browser.close()
print('PASS: filters, gallery, mobile menu/Escape, service login redirect, stylist and branch preselection, booking slots, 320–1440px layouts, photos, local fonts, reduced motion, no-JavaScript navigation; no JavaScript errors or external requests.')
