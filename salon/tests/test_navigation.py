from datetime import timedelta
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit
from unittest.mock import patch
from django.db import IntegrityError
from django.test import TestCase
from django.urls import resolve, reverse
from django.utils import timezone
from salon.models import Invoice, Appointment, Service
from .test_workflows import Fixtures


class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.links = []; self.forms = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a' and attrs.get('href'):
            self.links.append(attrs['href'])
        if tag == 'form':
            self.forms.append(attrs.get('action', ''))


class NavigationTests(Fixtures, TestCase):
    def setUp(self):
        self.make_data()
        self.booking = self.reserve()
        completed = self.reserve(customer=self.other_customer, start=self.booking.end_at)
        completed.status = 'completed'; completed.save(update_fields=['status'])
        Invoice.objects.create(appointment=completed, total=completed.total, method='cash', cashier=self.manager)
        self.other_invoice_booking = completed

    def crawl(self, user, paths):
        if user: self.client.force_login(user)
        else: self.client.logout()
        queue = list(paths); seen = set()
        while queue:
            url = queue.pop(0)
            if url in seen: continue
            seen.add(url)
            self.assertLess(len(seen), 200, 'Unexpected navigation loop')
            response = self.client.get(url)
            self.assertIn(response.status_code, (200, 302), (url, response.status_code))
            if response.status_code != 200 or 'text/html' not in response.get('Content-Type', ''): continue
            parser = Links(); parser.feed(response.content.decode())
            for action in parser.forms:
                self.assertIsNotNone(resolve(urlsplit(urljoin(url, action)).path))
            for href in parser.links:
                absolute = urlsplit(urljoin('http://testserver' + url, href))
                if absolute.netloc != 'testserver' or absolute.scheme not in ('http', 'https'): continue
                next_url = absolute.path + ('?' + absolute.query if absolute.query else '')
                if next_url not in seen: queue.append(next_url)
        return seen

    def test_all_visible_links_and_form_targets_resolve_for_each_role(self):
        public = ['/', '/tim-kiem/', '/dang-nhap/', '/dang-ky/']
        private = ['/tai-khoan/', '/dat-lich/', '/lich-cua-toi/', f'/lich-hen/{self.booking.pk}/']
        staff = ['/quan-ly/', '/quan-ly/ca-lam/', '/quan-ly/bao-cao/',
                 '/quan-ly/khach-hang/', '/quan-ly/dich-vu/', '/quan-ly/chi-nhanh/']
        for user, starts in [(None, public), (self.customer, public + private),
                             (self.receptionist, public + staff),
                             (self.manager, public + staff + ['/quan-ly/thiet-lap/'])]:
            with self.subTest(role=user.role if user else 'anonymous'):
                seen = self.crawl(user, starts)
                self.assertIn('/tim-kiem/', seen)
                if user and user.is_manager:
                    self.assertIn('/quan-ly/thiet-lap/ca-lam/', seen)
                    self.assertIn('/quan-ly/thiet-lap/dich-vu/nhap/', seen)

    def test_invalid_filters_do_not_crash_or_export_an_unvalidated_report(self):
        self.client.force_login(self.manager)
        for params in [{'branch':'²'}, {'branch':'9'*5000}, {'date':'0001-01-01'}, {'date':'9999-12-31'}]:
            self.assertEqual(self.client.get('/quan-ly/', params).status_code, 200)
        for params in [{'start':''}, {'end':'0001-01-01'}, {'end':'9999-12-31'},
                       {'start':'invalid'}, {'start':'2026-10-30','end':'2026-10-01'}, {'branch':'²'}]:
            response = self.client.get('/quan-ly/bao-cao/', params)
            self.assertEqual(response.status_code, 200)
            if response.context['filter_form'].errors:
                self.assertNotContains(response, 'Xuất Excel')
                self.assertContains(response, 'Đặt lại bộ lọc')
        response = self.client.get('/quan-ly/bao-cao/xuat/pdf/', {'end':'0001-01-01'})
        self.assertEqual(response.status_code, 400)

    def test_empty_submissions_render_errors_without_business_writes(self):
        self.client.force_login(self.manager)
        before = Appointment.objects.count(), Service.objects.count()
        for key in ('dich-vu','chi-nhanh','stylist','ghe','ca-lam','tai-khoan'):
            response = self.client.post(f'/quan-ly/thiet-lap/{key}/them/', {})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['form'].errors)
            self.assertEqual(self.client.post(f'/quan-ly/thiet-lap/{key}/nhap/', {}).status_code, 200)
        response = self.client.post(f'/quan-ly/thiet-lap/dich-vu/{self.service.pk}/xoa/', {})
        self.assertEqual(response.status_code, 200)
        response = self.client.post('/dat-lich/', {})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)
        self.assertEqual(before, (Appointment.objects.count(), Service.objects.count()))

    def test_near_booking_has_explanation_instead_of_invalid_action_links(self):
        self.client.force_login(self.customer)
        with patch('salon.views.timezone.now', return_value=self.booking.start_at-timedelta(minutes=30)):
            response = self.client.get(reverse('appointment_detail', args=[self.booking.pk]))
        self.assertContains(response, 'Đã sát giờ hẹn')
        self.assertNotContains(response, 'Đổi lịch hẹn</a>')
        with patch('salon.features.timezone.now', return_value=self.booking.start_at-timedelta(minutes=30)):
            response = self.client.get(reverse('my_appointments'))
        self.assertContains(response, 'Đã sát giờ hẹn')
        self.assertNotContains(response, '>Đổi lịch</a>')

    def test_registration_race_is_a_field_error_not_a_server_error(self):
        with patch('salon.features.RegisterForm.save', side_effect=IntegrityError):
            response = self.client.post('/dang-ky/', {'username':'new-customer','full_name':'Khách mới',
                'phone':'0901234567','email':'test@example.com','password1':'Fresh@Password2026','password2':'Fresh@Password2026'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tên đăng nhập vừa được sử dụng')

    def test_invalid_chair_selection_keeps_booking_and_returns_a_message(self):
        self.client.force_login(self.manager)
        with patch('salon.services.timezone.now', return_value=self.booking.start_at):
            for chair in ('²', '9'*5000, 'not-a-chair'):
                response = self.client.post(reverse('appointment_action', args=[self.booking.pk]), {'action':'checkin','chair':chair})
                self.assertEqual(response.status_code, 302)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, 'booked')
