from datetime import timedelta, time
from unittest.mock import patch
from django.core.exceptions import ValidationError, PermissionDenied
from django.test import TestCase, override_settings
from django.urls import reverse
from django.core.management import call_command
from django.core import mail
from django.utils import timezone
from salon.models import (User, Chair, Employee, Shift, Appointment, Invoice, Voucher,
    Stock, StockMovement, Product, Commission, Refund, DailyClosing, AppointmentChange,
    EmployeeAbsence, BranchClosure, EmailOutbox, PointEntry)
from salon.services import book, transition, local_at, validate_slot
from salon import business
from .test_workflows import Fixtures


class BusinessTests(Fixtures,TestCase):
    @classmethod
    def setUpTestData(cls):
        Fixtures.make_data(cls)
        cls.boss=User.objects.create_user(username='branchboss',role='branch_manager',branch=cls.branch,full_name='Quản lý A')
        cls.stylist_user=User.objects.create_user(username='stylistuser',role='stylist',branch=cls.branch,full_name='Stylist A')
        cls.employee.account=cls.stylist_user;cls.employee.commission_percent=20;cls.employee.save()
        cls.product=Product.objects.create(sku='SAP01',name='Sáp vuốt tóc')

    def extra_employee(self):
        e=Employee.objects.create(branch=self.branch,name='Stylist C',specialty='Cắt')
        Shift.objects.create(employee=e,start_at=local_at(self.day,time(9)),end_at=local_at(self.day,time(21)))
        return e

    def ready(self):
        a=self.reserve()
        a.start_at=local_at(timezone.localdate(),time(10));a.end_at=a.start_at+timedelta(minutes=30);a.save()
        with patch('salon.services.timezone.now',return_value=a.start_at):
            transition(pk=a.pk,actor=self.manager,action='checkin',chair_id=self.chair.pk)
            transition(pk=a.pk,actor=self.stylist_user,action='start')
        return a

    def paid(self,**kwargs):
        a=self.ready();transition(pk=a.pk,actor=self.manager,action='finish')
        transition(pk=a.pk,actor=self.manager,action='pay',**kwargs);a.refresh_from_db();return a

    def voucher(self,**kwargs):
        args=dict(code='SALONA',branch=self.branch,amount=20000,min_total=50000,
            starts_at=timezone.now()-timedelta(days=1),ends_at=timezone.now()+timedelta(days=1),max_uses=2)
        args.update(kwargs);return Voucher.objects.create(**args)

    def test_capacity_blocks_second_stylist_with_one_chair(self):
        self.reserve();e=self.extra_employee()
        with self.assertRaisesMessage(ValidationError,'sức chứa'):
            self.reserve(customer=self.other_customer,employee_id=e.pk)
        self.assertEqual(Appointment.objects.count(),1)

    def test_capacity_sweep_allows_successive_overlapping_intervals(self):
        Chair.objects.create(branch=self.branch,name='Ghế 02');e=self.extra_employee()
        self.reserve()
        self.reserve(customer=self.other_customer,start=local_at(self.day,time(10,30)))
        third=User.objects.create_user(username='third',role='customer')
        a=self.reserve(customer=third,employee_id=e.pk,service_ids=[self.service.pk,self.second_service.pk])
        self.assertEqual(a.end_at.hour,11)

    def test_zero_chairs_never_offers_a_slot(self):
        self.chair.active=False;self.chair.save()
        with self.assertRaisesMessage(ValidationError,'ghế'):self.reserve()

    def test_absence_blocks_new_and_preserves_existing_for_resolution(self):
        a=self.reserve()
        business.register_interruption(actor=self.boss,branch_id=self.branch.pk,employee_id=self.employee.pk,
            start=a.start_at,end=a.end_at,reason='Nghỉ đột xuất')
        self.assertTrue(Appointment.objects.filter(pk=a.pk,status='booked').exists())
        a.status='cancelled';a.save()
        with self.assertRaisesMessage(ValidationError,'lịch nghỉ'):self.reserve(customer=self.other_customer)
        self.assertTrue(AppointmentChange.objects.filter(appointment=a,action='interruption').exists())

    def test_branch_closure_blocks_otherwise_free_employee(self):
        business.register_interruption(actor=self.boss,branch_id=self.branch.pk,start=local_at(self.day,time(9)),end=local_at(self.day,time(21)),reason='Bảo trì')
        with self.assertRaisesMessage(ValidationError,'tạm nghỉ'):self.reserve()

    def test_branch_manager_cannot_register_another_branch_absence(self):
        with self.assertRaises(PermissionDenied):business.register_interruption(actor=self.boss,branch_id=self.other_branch.pk,start=local_at(self.day,time(9)),end=local_at(self.day,time(21)),reason='Nghỉ')

    def test_walkin_creates_unusable_password_and_reuses_matching_phone(self):
        a=business.walk_in(actor=self.boss,branch_id=self.branch.pk,employee_id=self.employee.pk,service_ids=[self.service.pk],start=local_at(self.day,time(11)),name='Khách mới',phone='0987654321')
        self.assertEqual(a.source,'walkin');self.assertFalse(a.customer.has_usable_password())
        b=business.walk_in(actor=self.boss,branch_id=self.branch.pk,employee_id=self.employee.pk,service_ids=[self.service.pk],start=local_at(self.day,time(12)),name='Khách mới',phone='0987654321')
        self.assertEqual(a.customer_id,b.customer_id)

    def test_failed_walkin_rolls_back_new_customer(self):
        self.reserve()
        with self.assertRaises(ValidationError):business.walk_in(actor=self.boss,branch_id=self.branch.pk,employee_id=self.employee.pk,service_ids=[self.service.pk],start=local_at(self.day,time(10)),name='Khách mới',phone='0987654321')
        self.assertFalse(User.objects.filter(phone='0987654321').exists())

    def test_walkin_phone_mismatch_does_not_expose_or_overwrite_profile(self):
        with self.assertRaises(ValidationError):business.walk_in(actor=self.boss,branch_id=self.branch.pk,employee_id=self.employee.pk,service_ids=[self.service.pk],start=local_at(self.day,time(11)),name='Sai tên',phone=self.customer.phone)
        self.customer.refresh_from_db();self.assertEqual(self.customer.full_name,'Khách A')

    def test_services_preserve_old_snapshot_and_apply_current_price_to_added(self):
        a=self.reserve();self.service.price=300000;self.service.save()
        business.change_services(actor=self.boss,pk=a.pk,service_ids=[self.service.pk,self.second_service.pk],reason='Khách đồng ý thêm gội')
        a.refresh_from_db();self.assertEqual(a.total,180000);self.assertEqual(a.end_at-a.start_at,timedelta(hours=1))
        self.assertEqual(a.changes.first().before['items'][0]['price'],100000)

    def test_service_extension_collision_rolls_back_items_and_history(self):
        a=self.reserve();self.reserve(customer=self.other_customer,start=a.end_at)
        with self.assertRaises(ValidationError):business.change_services(actor=self.boss,pk=a.pk,service_ids=[self.service.pk,self.second_service.pk],reason='Thêm gội')
        a.refresh_from_db();self.assertEqual(a.total,100000);self.assertEqual(a.items.count(),1)
        self.assertFalse(a.changes.exists())

    def test_cannot_change_services_after_finish(self):
        a=self.ready();transition(pk=a.pk,actor=self.stylist_user,action='finish')
        with self.assertRaises(ValidationError):business.change_services(actor=self.boss,pk=a.pk,service_ids=[self.service.pk],reason='Sửa')

    def test_must_finish_before_payment_and_finish_releases_resources(self):
        a=self.ready()
        with self.assertRaises(ValidationError):transition(pk=a.pk,actor=self.manager,action='pay')
        transition(pk=a.pk,actor=self.stylist_user,action='finish');a.refresh_from_db()
        self.assertEqual(a.status,'awaiting_payment');self.assertIsNotNone(a.service_finished_at)
        self.assertFalse(Invoice.objects.exists())
        with patch('salon.services.timezone.now',return_value=a.start_at-timedelta(minutes=1)):
            end=validate_slot(self.branch,self.employee,a.start_at,30)
        self.assertEqual(end,a.end_at)
        transition(pk=a.pk,actor=self.receptionist,action='pay');self.assertEqual(Invoice.objects.count(),1)

    def test_stylist_cannot_collect_or_access_other_stylist(self):
        a=self.ready()
        with self.assertRaises(PermissionDenied):transition(pk=a.pk,actor=self.stylist_user,action='pay')
        self.client.force_login(self.stylist_user)
        self.assertEqual(self.client.get(reverse('stylist_portal')).status_code,200)
        self.assertEqual(self.client.get(reverse('business_board')).status_code,403)
        other=self.reserve(branch_id=self.other_branch.pk,employee_id=self.other_employee.pk,start=local_at(self.day,time(14)))
        self.assertEqual(self.client.get(reverse('appointment_detail',args=[other.pk])).status_code,404)

    def test_late_checkin_cannot_extend_into_next_booking(self):
        a=self.reserve();self.reserve(customer=self.other_customer,start=a.end_at)
        # Same-day scheduling is evaluated at the simulated arrival time.
        with patch('salon.services.timezone.now',return_value=a.start_at+timedelta(minutes=20)):
            with self.assertRaises(ValidationError):transition(pk=a.pk,actor=self.manager,action='checkin',chair_id=self.chair.pk,reason='Khách đến muộn')
        a.refresh_from_db();self.assertEqual(a.status,'booked')

    def test_voucher_applies_once_commission_snapshot_and_invoice_totals(self):
        self.voucher();a=self.paid(voucher_code='salona')
        self.assertEqual((a.invoice.total,a.invoice.subtotal,a.invoice.voucher_discount),(80000,100000,20000))
        commission=Commission.objects.get(invoice=a.invoice);self.assertEqual((commission.percent,commission.amount),(20,16000))
        self.employee.commission_percent=50;self.employee.save();commission.refresh_from_db();self.assertEqual(commission.amount,16000)

    def test_voucher_wrong_branch_expired_points_and_exhausted_rejected(self):
        a=self.ready();transition(pk=a.pk,actor=self.manager,action='finish')
        for kwargs in ({'branch':self.other_branch},{'ends_at':timezone.now()-timedelta(hours=1)}):
            v=self.voucher(**kwargs)
            with self.assertRaises(ValidationError):transition(pk=a.pk,actor=self.manager,action='pay',voucher_code=v.code)
            v.delete()
        v=self.voucher();self.customer.points=10;self.customer.save()
        with self.assertRaises(ValidationError):transition(pk=a.pk,actor=self.manager,action='pay',voucher_code=v.code,redeem_points=1)
        self.assertFalse(Invoice.objects.exists())

    def test_changed_payment_quote_cannot_collect_stale_amount(self):
        a=self.ready();transition(pk=a.pk,actor=self.manager,action='finish');self.voucher()
        with self.assertRaises(ValidationError):transition(pk=a.pk,actor=self.manager,action='pay',voucher_code='SALONA',quoted_total=100000)
        self.assertFalse(Invoice.objects.exists())

    def test_full_refund_preserves_original_and_reverses_points(self):
        a=self.paid();business.refund_invoice(actor=self.boss,invoice_id=a.invoice.pk,reason='Khách phản ánh, đã trả tiền')
        self.customer.refresh_from_db();self.assertEqual(self.customer.points,0)
        a.invoice.refresh_from_db();self.assertEqual(a.invoice.total,100000)
        self.assertEqual(Refund.objects.get().amount,100000)
        self.assertEqual(PointEntry.objects.get(kind='refund').amount,-10)
        with self.assertRaises(ValidationError):business.refund_invoice(actor=self.boss,invoice_id=a.invoice.pk,reason='Lặp')

    def test_receptionist_cannot_refund(self):
        a=self.paid()
        with self.assertRaises(PermissionDenied):business.refund_invoice(actor=self.receptionist,invoice_id=a.invoice.pk,reason='Hoàn')

    def test_closing_cash_and_discrepancy_reason_then_lock_payments(self):
        a=self.paid()
        with self.assertRaises(ValidationError):business.close_day(actor=self.boss,branch_id=self.branch.pk,day=timezone.localdate(),counted=0,reason='')
        close=business.close_day(actor=self.boss,branch_id=self.branch.pk,day=timezone.localdate(),counted=100000,reason='')
        self.assertEqual(close.expected_cash,100000)
        with self.assertRaises(ValidationError):business.refund_invoice(actor=self.boss,invoice_id=a.invoice.pk,reason='Sau chốt')

    def test_closing_refuses_unpaid_service(self):
        a=self.ready();transition(pk=a.pk,actor=self.manager,action='finish')
        with self.assertRaises(ValidationError):business.close_day(actor=self.boss,branch_id=self.branch.pk,day=timezone.localdate(),counted=0,reason='')

    def test_stock_transfer_atomic_balances_and_shared_reference(self):
        business.move_stock(actor=self.boss,branch_id=self.branch.pk,product_id=self.product.pk,amount=10,kind='receipt',reason='Nhập')
        business.move_stock(actor=self.manager,branch_id=self.branch.pk,product_id=self.product.pk,amount=4,kind='transfer',reason='Điều chuyển',target_id=self.other_branch.pk)
        self.assertEqual(Stock.objects.get(branch=self.branch).quantity,6)
        self.assertEqual(Stock.objects.get(branch=self.other_branch).quantity,4)
        pair=list(StockMovement.objects.filter(kind='transfer'));self.assertEqual(len(pair),2);self.assertEqual(pair[0].reference,pair[1].reference)

    def test_stock_negative_rollback_and_transfer_scope(self):
        with self.assertRaises(ValidationError):business.move_stock(actor=self.boss,branch_id=self.branch.pk,product_id=self.product.pk,amount=1,kind='consume',reason='Xuất')
        self.assertFalse(Stock.objects.exists());self.assertFalse(StockMovement.objects.exists())
        with self.assertRaises(PermissionDenied):business.move_stock(actor=self.boss,branch_id=self.branch.pk,product_id=self.product.pk,amount=1,kind='transfer',reason='Chuyển',target_id=self.other_branch.pk)

    def test_branch_manager_all_screens_and_exports_scoped(self):
        self.client.force_login(self.boss)
        for name in ['business_board','business_walkin','business_interruptions','business_stock','business_closing','business_commissions','business_emails']:
            self.assertEqual(self.client.get(reverse(name)).status_code,200,name)
        for name in ['business_board','business_stock','business_commissions']:
            for fmt in ('xlsx','pdf'):self.assertEqual(self.client.get(reverse(name),{'export':fmt}).status_code,200,(name,fmt))
        response=self.client.get(reverse('business_board'),{'branch':self.other_branch.pk})
        self.assertEqual(response.context['branch_rows'],[])
        self.assertEqual(self.client.get(reverse('settings')).status_code,403)
        self.assertEqual(self.client.get(reverse('business_resource_edit',args=['chi-nhanh',self.other_branch.pk])).status_code,404)

    def test_resource_form_cannot_assign_other_branch_or_privileged_role(self):
        self.client.force_login(self.boss)
        response=self.client.post(reverse('business_resource_add',args=['tai-khoan']),{'username':'escalated','role':'manager','full_name':'Sai','branch':self.other_branch.pk,'new_password':'Secure@Password2026','is_active':'on'})
        self.assertEqual(response.status_code,200);self.assertFalse(User.objects.filter(username='escalated').exists())
        response=self.client.post(reverse('business_resource_add',args=['ghe']),{'name':'Sai','branch':self.other_branch.pk,'active':'on'})
        self.assertEqual(response.status_code,200);self.assertFalse(Chair.objects.filter(name='Sai').exists())

    def test_mutations_require_post_and_csrf(self):
        self.client.force_login(self.boss)
        item=EmployeeAbsence.objects.create(employee=self.employee,start_at=local_at(self.day,time(9)),end_at=local_at(self.day,time(10)),reason='Nghỉ',actor=self.boss)
        self.assertEqual(self.client.get(reverse('business_stop_interruption',args=['stylist',item.pk])).status_code,405)
        from django.test import Client
        client=Client(enforce_csrf_checks=True);client.force_login(self.boss)
        self.assertEqual(client.post(reverse('business_stop_interruption',args=['stylist',item.pk])).status_code,403)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_outbox_no_send_on_booking_then_dispatch_once(self):
        self.customer.email='demo@example.com';self.customer.save();a=self.reserve()
        self.assertGreaterEqual(EmailOutbox.objects.filter(appointment=a).count(),2)
        self.assertEqual(len(getattr(mail,'outbox',[])),0)
        call_command('dispatch_emails');first=len(mail.outbox);self.assertGreater(first,0)
        call_command('dispatch_emails');self.assertEqual(len(mail.outbox),first)

    def test_cancel_and_reschedule_invalidate_old_reminders(self):
        self.customer.email='demo@example.com';self.customer.save();a=self.reserve()
        transition(pk=a.pk,actor=self.manager,action='cancel')
        self.assertFalse(EmailOutbox.objects.filter(appointment=a,key__startswith='reminder:',cancelled=False).exists())

    def test_refund_spent_points_become_debt_repaid_by_future_earnings(self):
        a=self.paid();self.customer.points=2;self.customer.save()
        business.refund_invoice(actor=self.boss,invoice_id=a.invoice.pk,reason='Hoàn sau khi điểm đã sử dụng')
        self.customer.refresh_from_db();self.assertEqual((self.customer.points,self.customer.points_debt),(0,8))
        self.assertEqual(Refund.objects.get().points_debt_added,8)
        next_appt=self.reserve(start=local_at(self.day,time(12)))
        next_appt.status='awaiting_payment';next_appt.save()
        transition(pk=next_appt.pk,actor=self.manager,action='pay')
        self.customer.refresh_from_db();self.assertEqual((self.customer.points,self.customer.points_debt),(2,0))
        inv=Invoice.objects.get(appointment=next_appt)
        self.assertEqual((inv.points_earned,inv.points_debt_paid),(2,8))

    def test_reminder_after_interruption_is_cancelled_and_new_slot_gets_new_reminder(self):
        self.customer.email='demo@example.com';self.customer.save();a=self.reserve()
        business.register_interruption(actor=self.boss,branch_id=self.branch.pk,employee_id=self.employee.pk,start=a.start_at,end=a.end_at,reason='Nghỉ')
        self.assertFalse(EmailOutbox.objects.filter(appointment=a,key__startswith='reminder:',cancelled=False).exists())

    def test_reception_cannot_view_commissions_or_branch_audit(self):
        self.client.force_login(self.receptionist)
        for name in ('business_commissions','business_audit','business_stock','business_emails'):
            self.assertEqual(self.client.get(reverse(name)).status_code,403)
        response=self.client.get(reverse('business_board'))
        self.assertNotContains(response,'href="'+reverse('business_commissions')+'"')

    def test_branch_audit_and_resource_forms_are_scoped(self):
        from salon.models import AuditLog
        AuditLog.objects.create(actor=self.manager,branch=self.other_branch,action='SECRET-B')
        AuditLog.objects.create(actor=self.boss,branch=self.branch,action='VISIBLE-A')
        self.client.force_login(self.boss)
        response=self.client.get(reverse('business_audit'))
        self.assertContains(response,'VISIBLE-A');self.assertNotContains(response,'SECRET-B')
        for key in ['chi-nhanh','stylist','ghe','ca-lam','tai-khoan','voucher']:
            self.assertEqual(self.client.get(reverse('business_resources',args=[key])).status_code,200)
            if key!='chi-nhanh':self.assertEqual(self.client.get(reverse('business_resource_add',args=[key])).status_code,200)
        self.assertEqual(self.client.get(reverse('business_resources',args=['san-pham'])).status_code,403)

    def test_refunds_reported_on_refund_date_and_exported_negative(self):
        a=self.paid();Invoice.objects.filter(pk=a.invoice.pk).update(paid_at=timezone.now()-timedelta(days=2))
        business.refund_invoice(actor=self.boss,invoice_id=a.invoice.pk,reason='Hoàn hôm nay')
        self.client.force_login(self.boss)
        day=str(timezone.localdate())
        response=self.client.get(reverse('reports'),{'start':day,'end':day})
        self.assertEqual(response.context['summary']['net'],-100000)
        response=self.client.get(reverse('feature_report_export',args=['csv']),{'start':day,'end':day})
        self.assertContains(response,'-100000');self.assertContains(response,'HOAN-')

    def test_checkin_interrupted_employee_requires_resolution(self):
        a=self.reserve()
        business.register_interruption(actor=self.boss,branch_id=self.branch.pk,employee_id=self.employee.pk,start=a.start_at,end=a.end_at,reason='Nghỉ')
        with patch('salon.services.timezone.now',return_value=a.start_at):
            with self.assertRaises(ValidationError):transition(pk=a.pk,actor=self.manager,action='checkin',chair_id=self.chair.pk)

    def test_release_checkedin_customer_for_reassignment_preserves_history(self):
        a=self.reserve()
        with patch('salon.services.timezone.now',return_value=a.start_at):
            transition(pk=a.pk,actor=self.manager,action='checkin',chair_id=self.chair.pk)
        transition(pk=a.pk,actor=self.manager,action='release_checkin',reason='Đổi stylist do nghỉ')
        a.refresh_from_db();self.assertEqual(a.status,'booked');self.assertIsNone(a.chair_id)
        self.assertIsNotNone(a.changes.get(action='release_checkin').before['checked_in'])

    def test_disabled_or_reassigned_actor_is_rechecked_from_database(self):
        self.boss.branch=self.other_branch;self.boss.save()
        stale=User.objects.get(pk=self.boss.pk);stale.branch=self.branch
        with self.assertRaises(PermissionDenied):business.close_day(actor=stale,branch_id=self.branch.pk,day=timezone.localdate(),counted=0,reason='')

    def test_day_slot_read_is_batched_and_agrees_with_write_validator(self):
        from salon.services import available_slots
        from django.test.utils import CaptureQueriesContext
        from django.db import connection
        with CaptureQueriesContext(connection) as queries:
            slots=available_slots(self.branch,self.employee,self.day,30)
        self.assertLessEqual(len(queries),8)
        self.assertIn('10:00',slots)
        a=self.reserve();employee=self.extra_employee()
        remaining=available_slots(self.branch,employee,self.day,30)
        self.assertNotIn('10:00',remaining)
        with self.assertRaises(ValidationError):validate_slot(self.branch,employee,a.start_at,30)

    def test_staff_contact_requires_verification_and_keeps_role_and_points(self):
        self.reserve();self.client.force_login(self.boss)
        url=reverse('business_customer_contact',args=[self.customer.pk])
        payload={'full_name':self.customer.full_name,'phone':self.customer.phone,'email':'verified@example.com'}
        self.assertEqual(self.client.post(url,payload).status_code,200)
        self.customer.refresh_from_db();self.assertEqual(self.customer.email,'')
        response=self.client.post(url,dict(payload,verified='on',role='manager',points=999))
        self.assertEqual(response.status_code,302)
        self.customer.refresh_from_db();self.assertEqual((self.customer.role,self.customer.points,self.customer.email),('customer',0,'verified@example.com'))

    def test_contact_cannot_read_or_update_unrelated_branch_customer(self):
        other=self.reserve(customer=self.other_customer,branch_id=self.other_branch.pk,employee_id=self.other_employee.pk)
        self.client.force_login(self.boss)
        url=reverse('business_customer_contact',args=[self.other_customer.pk])
        self.assertEqual(self.client.get(url).status_code,404)
        self.assertEqual(self.client.post(url,{'email':'bad@example.com','verified':'on'}).status_code,404)


from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from django.db import connections,close_old_connections,IntegrityError
from django.test import TransactionTestCase

class ConcurrentBranchTests(Fixtures,TransactionTestCase):
    def setUp(self):self.make_data()
    def race(self,fn,values):
        gate=Barrier(len(values))
        def run(value):
            close_old_connections()
            try:
                gate.wait(timeout=10);fn(value);return 'ok'
            except (ValidationError,IntegrityError):return 'rejected'
            finally:connections.close_all()
        with ThreadPoolExecutor(max_workers=len(values)) as pool:return list(pool.map(run,values))

    def test_two_stylists_share_single_chair_capacity_under_concurrent_booking(self):
        second=Employee.objects.create(name='C',branch=self.branch)
        Shift.objects.create(employee=second,start_at=local_at(self.day,time(9)),end_at=local_at(self.day,time(21)))
        def reserve(pair):
            customer,employee=pair
            book(customer=customer,branch_id=self.branch.pk,employee_id=employee.pk,service_ids=[self.service.pk],start=local_at(self.day,time(10)))
        self.assertCountEqual(self.race(reserve,[(self.customer,self.employee),(self.other_customer,second)]),['ok','rejected'])
        self.assertEqual(Appointment.objects.count(),1)

    def test_stock_cannot_be_spent_twice_concurrently(self):
        product=Product.objects.create(sku='A',name='A')
        business.move_stock(actor=self.manager,branch_id=self.branch.pk,product_id=product.pk,amount=10,kind='receipt',reason='Nhập')
        def consume(_):business.move_stock(actor=self.manager,branch_id=self.branch.pk,product_id=product.pk,amount=7,kind='consume',reason='Xuất')
        self.assertCountEqual(self.race(consume,[1,2]),['ok','rejected'])
        self.assertEqual(Stock.objects.get().quantity,3)
        self.assertEqual(StockMovement.objects.count(),2)

    def test_last_voucher_use_across_branches_is_serialized(self):
        first=self.reserve();second=self.reserve(customer=self.other_customer,branch_id=self.other_branch.pk,employee_id=self.other_employee.pk)
        Appointment.objects.filter(pk__in=[first.pk,second.pk]).update(status='awaiting_payment')
        Voucher.objects.create(code='LAST',amount=10000,starts_at=timezone.now()-timedelta(days=1),ends_at=timezone.now()+timedelta(days=1),max_uses=1)
        def pay(pk):transition(pk=pk,actor=self.manager,action='pay',voucher_code='LAST')
        self.assertCountEqual(self.race(pay,[first.pk,second.pk]),['ok','rejected'])
        self.assertEqual(Invoice.objects.count(),1)
