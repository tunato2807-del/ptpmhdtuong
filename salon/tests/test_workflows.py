from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta, time
from threading import Barrier
from unittest.mock import patch
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import IntegrityError, transaction, close_old_connections, connections
from django.test import TestCase, TransactionTestCase, Client
from django.urls import reverse
from django.utils import timezone
from salon.models import (User, Branch, Service, Employee, Shift, Chair, Appointment,
                          Invoice, Review, Notification, AuditLog)
from salon.services import book, transition, available_slots, local_at
from salon.forms import ShiftForm

class Fixtures:
    def make_data(self):
        self.day = timezone.localdate()+timedelta(days=1)
        self.branch = Branch.objects.create(name='Salon A',address='TP.HCM',phone='0901234567',opens_at=time(9),closes_at=time(21))
        self.other_branch = Branch.objects.create(name='Salon B',address='TP.HCM',phone='0901234568',opens_at=time(9),closes_at=time(21))
        self.employee = Employee.objects.create(name='Stylist A',branch=self.branch,specialty='Fade')
        self.other_employee = Employee.objects.create(name='Stylist B',branch=self.other_branch,specialty='Layer')
        for e in [self.employee,self.other_employee]:
            for d in [timezone.localdate(),self.day]:
                Shift.objects.create(employee=e,start_at=local_at(d,time(9)),end_at=local_at(d,time(21)))
        self.chair = Chair.objects.create(branch=self.branch,name='Ghế 01')
        Chair.objects.create(branch=self.other_branch,name='Ghế B01')
        self.service = Service.objects.create(name='Cắt',price=100000,duration=30)
        self.second_service = Service.objects.create(name='Gội',price=80000,duration=30)
        self.customer = User.objects.create_user(username='customer',password='Test@Password26',full_name='Khách A',phone='0901234567')
        self.other_customer = User.objects.create_user(username='other',password='Test@Password26',full_name='Khách B')
        self.receptionist = User.objects.create_user(username='reception',password='Test@Password26',role='receptionist',branch=self.branch,full_name='Lễ tân')
        self.manager = User.objects.create_user(username='manager',password='Test@Password26',role='manager',is_staff=True,is_superuser=True)

    def reserve(self, **overrides):
        args = dict(customer=self.customer,branch_id=self.branch.pk,employee_id=self.employee.pk,
                    service_ids=[self.service.pk],start=local_at(self.day,time(10)))
        args.update(overrides)
        return book(**args)

class BookingTests(Fixtures, TestCase):
    def setUp(self): self.make_data()

    def test_snapshots_and_combined_duration(self):
        a = self.reserve(service_ids=[self.service.pk,self.second_service.pk])
        self.assertEqual(a.total,180000)
        self.assertEqual(a.end_at-a.start_at,timedelta(minutes=60))
        self.service.price = 200000; self.service.duration = 45; self.service.save()
        self.assertEqual(a.total,180000)
        self.assertEqual(Notification.objects.filter(recipient=self.customer).count(),1)
        self.assertEqual(AuditLog.objects.filter(appointment=a).count(),1)

    def test_stylist_overlap_rejected_but_adjacent_allowed(self):
        self.reserve()
        with self.assertRaises(ValidationError):
            self.reserve(customer=self.other_customer,start=local_at(self.day,time(10,15)))
        next_a = self.reserve(customer=self.other_customer,start=local_at(self.day,time(10,30)))
        self.assertEqual(next_a.start_at.hour,10)

    def test_database_blocks_bypass_of_stylist_conflict(self):
        a = self.reserve()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Appointment.objects.create(customer=self.other_customer,branch=self.branch,employee=self.employee,start_at=a.start_at,end_at=a.end_at)

    def test_customer_cannot_book_overlapping_other_branch(self):
        self.reserve()
        with self.assertRaises(ValidationError): self.reserve(branch_id=self.other_branch.pk,employee_id=self.other_employee.pk)

    def test_mismatched_branch_rejected(self):
        with self.assertRaises(ValidationError): self.reserve(employee_id=self.other_employee.pk)

    def test_outside_shift_and_closing_time(self):
        for clock in [time(8),time(20,45),time(10,7)]:
            with self.subTest(clock=clock), self.assertRaises(ValidationError): self.reserve(start=local_at(self.day,clock))
        Shift.objects.filter(employee=self.employee,start_at__date=self.day).delete()
        with self.assertRaises(ValidationError): self.reserve()

    def test_past_and_far_future_dates_rejected(self):
        for d in [timezone.localdate()-timedelta(days=1),self.day+timedelta(days=31)]:
            with self.subTest(day=d), self.assertRaises(ValidationError): self.reserve(start=local_at(d,time(10)))

    def test_inactive_service_and_branch_rejected(self):
        self.service.active=False; self.service.save()
        with self.assertRaises(ValidationError): self.reserve()
        self.service.active=True; self.service.save()
        self.branch.active=False; self.branch.save()
        with self.assertRaises(ValidationError): self.reserve()

    def test_availability_excludes_overlapping_duration(self):
        self.reserve()
        slots=available_slots(self.branch,self.employee,self.day,60)
        self.assertNotIn('09:15',slots)
        self.assertNotIn('10:00',slots)
        self.assertIn('10:30',slots)
        self.assertNotIn('20:15',slots)

    def test_cancel_releases_slot(self):
        a = self.reserve()
        transition(pk=a.pk,actor=self.customer,action='cancel')
        self.assertIn('10:00',available_slots(self.branch,self.employee,self.day,30))

    def test_customer_cannot_cancel_within_two_hours(self):
        a = self.reserve()
        with patch('salon.services.timezone.now',return_value=a.start_at-timedelta(minutes=90)):
            with self.assertRaises(ValidationError): transition(pk=a.pk,actor=self.customer,action='cancel')

    def test_no_show_only_after_end(self):
        a = self.reserve()
        with self.assertRaises(ValidationError): transition(pk=a.pk,actor=self.receptionist,action='no_show')
        with patch('salon.services.timezone.now',return_value=a.end_at+timedelta(minutes=1)):
            result=transition(pk=a.pk,actor=self.receptionist,action='no_show')
        self.assertEqual(result.status,'no_show')

    def test_operator_booking_records_actual_actor(self):
        a=self.reserve(actor=self.receptionist)
        self.assertEqual(a.customer,self.customer)
        self.assertEqual(AuditLog.objects.get(appointment=a).actor,self.receptionist)

    def test_staff_account_cannot_be_booked_as_customer(self):
        with self.assertRaises(ValidationError): self.reserve(customer=self.receptionist)

    def test_shift_admin_cannot_remove_coverage(self):
        self.reserve()
        shift=Shift.objects.get(employee=self.employee,start_at__date=self.day)
        form=ShiftForm(data={'employee':self.employee.pk,'start_at':local_at(self.day,time(11)),'end_at':local_at(self.day,time(21))},instance=shift)
        self.assertFalse(form.is_valid())

class CheckoutTests(Fixtures, TestCase):
    def setUp(self): self.make_data()
    def today_appointment(self):
        a = self.reserve()
        a.start_at = local_at(timezone.localdate(),time(10))
        a.end_at = a.start_at+timedelta(minutes=30)
        a.save()
        return a
    def start(self, a):
        with patch('salon.services.timezone.now',return_value=a.start_at):
            transition(pk=a.pk,actor=self.receptionist,action='checkin',chair_id=self.chair.pk)
            transition(pk=a.pk,actor=self.receptionist,action='start')

    def test_checkin_service_cash_payment_points_exactly_once(self):
        a=self.today_appointment(); self.start(a)
        transition(pk=a.pk,actor=self.receptionist,action='finish')
        transition(pk=a.pk,actor=self.receptionist,action='pay')
        a.refresh_from_db(); self.customer.refresh_from_db()
        self.assertEqual(a.status,'completed')
        self.assertEqual(a.invoice.total,100000)
        self.assertEqual(self.customer.points,10)
        with self.assertRaises(ValidationError): transition(pk=a.pk,actor=self.receptionist,action='pay')
        self.assertEqual(Invoice.objects.count(),1)
        self.customer.refresh_from_db(); self.assertEqual(self.customer.points,10)

    def test_mock_payment_requires_explicit_confirmation(self):
        a=self.today_appointment(); self.start(a)
        transition(pk=a.pk,actor=self.receptionist,action='finish')
        with self.assertRaises(ValidationError): transition(pk=a.pk,actor=self.receptionist,action='pay',method='mock')
        self.assertFalse(Invoice.objects.exists())
        transition(pk=a.pk,actor=self.receptionist,action='pay',method='mock',confirmation='confirmed')
        self.assertEqual(Invoice.objects.get().method,'mock')

    def test_payment_cannot_skip_checkin_and_service(self):
        a=self.today_appointment()
        for action in ['pay','start']:
            with self.subTest(action=action), self.assertRaises(ValidationError): transition(pk=a.pk,actor=self.receptionist,action=action)

    def test_checkin_only_on_scheduled_day(self):
        a=self.reserve()
        with self.assertRaises(ValidationError): transition(pk=a.pk,actor=self.receptionist,action='checkin',chair_id=self.chair.pk)

    def test_customer_cannot_operate_checkout(self):
        a=self.today_appointment()
        with self.assertRaises(PermissionDenied): transition(pk=a.pk,actor=self.customer,action='checkin',chair_id=self.chair.pk)

    def test_wrong_branch_and_occupied_chair_rejected(self):
        a=self.today_appointment()
        wrong=Chair.objects.create(branch=self.other_branch,name='Ghế khác')
        with self.assertRaises(ValidationError): transition(pk=a.pk,actor=self.receptionist,action='checkin',chair_id=wrong.pk)
        self.start(a)
        employee=Employee.objects.create(branch=self.branch,name='Stylist C')
        other=Appointment.objects.create(customer=self.other_customer,branch=self.branch,employee=employee,start_at=a.start_at,end_at=a.end_at)
        with self.assertRaises(ValidationError): transition(pk=other.pk,actor=self.receptionist,action='checkin',chair_id=self.chair.pk)

class WebTests(Fixtures, TestCase):
    def setUp(self): self.make_data()

    def test_public_and_protected_routes(self):
        for name in ['home','login','register','health']:
            with self.subTest(name=name): self.assertEqual(self.client.get(reverse(name)).status_code,200)
        for name in ['booking','dashboard','my_appointments']:
            with self.subTest(name=name): self.assertEqual(self.client.get(reverse(name)).status_code,302)

    def test_staff_templates_and_invalid_filters_render(self):
        self.reserve()
        self.client.force_login(self.manager)
        for name in ['dashboard','customers','catalog','branches','schedule','reports']:
            with self.subTest(name=name):
                response=self.client.get(reverse(name),{'date':self.day.isoformat()})
                self.assertEqual(response.status_code,200)
                self.assertContains(response,'GENTLEMAN')
        self.assertEqual(self.client.get(reverse('dashboard'),{'date':'invalid','branch':'x'}).status_code,200)

    def test_customer_templates_and_access_isolation(self):
        a=self.reserve()
        self.client.force_login(self.customer)
        for url in [reverse('booking'),reverse('my_appointments'),reverse('appointment_detail',args=[a.pk])]:
            self.assertEqual(self.client.get(url).status_code,200)
        self.assertEqual(self.client.get(reverse('dashboard')).status_code,403)
        self.client.force_login(self.other_customer)
        self.assertEqual(self.client.get(reverse('appointment_detail',args=[a.pk])).status_code,404)
        self.assertEqual(self.client.post(reverse('appointment_action',args=[a.pk]),{'action':'cancel'}).status_code,404)

    def test_receptionist_cannot_access_other_branch(self):
        a=self.reserve(branch_id=self.other_branch.pk,employee_id=self.other_employee.pk)
        self.client.force_login(self.receptionist)
        self.assertEqual(self.client.get(reverse('appointment_detail',args=[a.pk])).status_code,404)
        response=self.client.get(reverse('dashboard'),{'date':self.day.isoformat(),'branch':self.other_branch.pk})
        self.assertEqual(response.context['total_count'],0)
        with self.assertRaises(PermissionDenied): transition(pk=a.pk,actor=self.receptionist,action='cancel')

    def test_staff_booking_requires_scoped_customer(self):
        self.reserve(start=local_at(self.day,time(9)))
        self.client.force_login(self.receptionist)
        payload={'branch':self.branch.pk,'employee':self.employee.pk,'services':[self.service.pk],'date':self.day.isoformat(),'time':'11:00','customer':self.customer.pk}
        response=self.client.post(reverse('booking'),payload)
        self.assertEqual(response.status_code,302)
        self.assertEqual(Appointment.objects.get(start_at=local_at(self.day,time(11))).customer_id,self.customer.pk)
        payload['customer']=self.other_customer.pk; payload['time']='12:00'
        self.assertEqual(self.client.post(reverse('booking'),payload).status_code,200)
        self.assertEqual(Appointment.objects.count(),2)

    def test_registration_and_login_redirect_validation(self):
        response=self.client.post(reverse('register'),{'username':'new','full_name':'Khách mới','phone':'0901111222','email':'new@example.com','password1':'Distinct@Pass2026','password2':'Distinct@Pass2026'})
        self.assertRedirects(response,reverse('booking'))
        self.assertEqual(User.objects.get(username='new').role,'customer')
        self.client.post(reverse('logout'))
        response=self.client.post(reverse('login')+'?next=https://evil.example/',{'username':'new','password':'Distinct@Pass2026'})
        self.assertEqual(response.url,reverse('my_appointments'))

    def test_csrf_and_state_changes_require_post(self):
        a=self.reserve()
        csrf_client=Client(enforce_csrf_checks=True); csrf_client.force_login(self.customer)
        self.assertEqual(csrf_client.post(reverse('appointment_action',args=[a.pk]),{'action':'cancel'}).status_code,403)
        self.client.force_login(self.customer)
        self.assertEqual(self.client.get(reverse('appointment_action',args=[a.pk])).status_code,405)

    def test_slots_api_and_invalid_inputs(self):
        response=self.client.get(reverse('slots'),{'branch':self.branch.pk,'employee':self.employee.pk,'date':self.day.isoformat(),'services':[self.service.pk]})
        self.assertEqual(response.status_code,200); self.assertIn('10:00',response.json()['slots'])
        self.assertEqual(self.client.get(reverse('slots'),{'branch':'invalid'}).status_code,400)

    def test_end_to_end_booking_post_and_duplicate_rejection(self):
        self.client.force_login(self.customer)
        payload={'branch':self.branch.pk,'employee':self.employee.pk,'services':[self.service.pk],'date':self.day.isoformat(),'time':'10:00','note':'Giữ mái dài'}
        response=self.client.post(reverse('booking'),payload)
        self.assertEqual(response.status_code,302); self.assertEqual(Appointment.objects.count(),1)
        self.client.force_login(self.other_customer)
        self.assertContains(self.client.post(reverse('booking'),payload),'Khung giờ vừa được đặt')
        self.assertEqual(Appointment.objects.count(),1)

    def test_review_only_after_completed_and_once(self):
        a=self.reserve(); self.client.force_login(self.customer)
        self.assertEqual(self.client.post(reverse('review',args=[a.pk]),{'rating':5}).status_code,404)
        a.status='completed'; a.save()
        self.client.post(reverse('review',args=[a.pk]),{'rating':9})
        self.assertEqual(Review.objects.count(),0)
        self.client.post(reverse('review',args=[a.pk]),{'rating':5,'comment':'Tốt'})
        self.client.post(reverse('review',args=[a.pk]),{'rating':4})
        self.assertEqual(Review.objects.count(),1)

    def test_invoice_access_and_report_csv(self):
        a=self.reserve(); a.status='completed'; a.save()
        Invoice.objects.create(appointment=a,total=a.total,method='cash',cashier=self.manager)
        self.customer.full_name='=SUM(1+1)'; self.customer.save()
        self.client.force_login(self.manager)
        response=self.client.get(reverse('reports'),{'export':'csv'})
        self.assertContains(response,"'=SUM(1+1)")
        self.assertEqual(self.client.get(reverse('invoice',args=[a.pk])).status_code,200)
        self.client.force_login(self.other_customer)
        self.assertEqual(self.client.get(reverse('invoice',args=[a.pk])).status_code,404)

class ConcurrentBookingTests(Fixtures, TransactionTestCase):
    def setUp(self): self.make_data()

    def test_two_requests_for_same_stylist_only_one_succeeds(self):
        barrier=Barrier(2)
        def attempt(customer_id):
            close_old_connections()
            try:
                customer=User.objects.get(pk=customer_id)
                barrier.wait(timeout=10)
                book(customer=customer,branch_id=self.branch.pk,employee_id=self.employee.pk,
                     service_ids=[self.service.pk],start=local_at(self.day,time(10)))
                return 'booked'
            except (ValidationError,IntegrityError): return 'conflict'
            finally: connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as executor:
            results=list(executor.map(attempt,[self.customer.pk,self.other_customer.pk]))
        self.assertCountEqual(results,['booked','conflict'])
        self.assertEqual(Appointment.objects.count(),1)
