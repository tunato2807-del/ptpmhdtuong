"""Adversarial examples and measured budgets from the Agent Skills review."""

from datetime import timedelta, time
from unittest.mock import patch
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.db import connection
from django.test import TestCase, TransactionTestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from salon.models import (
    User,
    Branch,
    Chair,
    Employee,
    Shift,
    Appointment,
    AppointmentChange,
    Product,
    EmailOutbox,
)
from salon import business, business_views
from salon.services import transition, local_at
from .test_workflows import Fixtures


class QualityBoundaryTests(Fixtures, TestCase):
    @classmethod
    def setUpTestData(cls):
        Fixtures.make_data(cls)
        cls.boss = User.objects.create_user(
            username="quality-boss", role="branch_manager", branch=cls.branch
        )
        cls.stylist = User.objects.create_user(
            username="quality-stylist", role="stylist", branch=cls.branch
        )
        cls.employee.account = cls.stylist
        cls.employee.save()

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_branch_contact_cannot_replace_existing_login_mailbox(self):
        cache.clear()
        self.customer.email = "owner@example.test"
        self.customer.save()
        self.reserve()
        self.reserve(
            branch_id=self.other_branch.pk,
            employee_id=self.other_employee.pk,
            start=local_at(self.day, time(12)),
        )
        self.client.force_login(self.boss)
        response = self.client.post(
            reverse("business_customer_contact", args=[self.customer.pk]),
            {
                "full_name": self.customer.full_name,
                "phone": self.customer.phone,
                "email": "attacker@example.test",
                "verified": "on",
            },
        )
        self.assertIn(response.status_code, (200, 302))
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.email, "owner@example.test")
        self.assertFalse(EmailOutbox.objects.filter(recipient="attacker@example.test").exists())
        self.client.logout()
        self.client.post(reverse("password_reset"), {"email": "attacker@example.test"})
        self.assertEqual(len(mail.outbox), 0)

    def test_stylist_assignment_is_rechecked_after_waiting_for_branch_lock(self):
        a = self.reserve()
        a.status = "in_service"
        a.save()
        original = Branch.objects.select_for_update

        def revoke(*args, **kwargs):
            Employee.objects.filter(pk=self.employee.pk).update(account=None)
            return original(*args, **kwargs)

        with patch.object(Branch.objects, "select_for_update", side_effect=revoke):
            with self.assertRaises(PermissionDenied):
                transition(pk=a.pk, actor=self.stylist, action="finish")
        a.refresh_from_db()
        self.assertEqual(a.status, "in_service")

    def test_chain_only_create_is_rechecked_after_role_change(self):
        self.client.force_login(self.manager)
        original = business_views.get_object_or_404

        def demote(klass, *args, **kwargs):
            if klass is User and kwargs.get("pk") == self.manager.pk:
                User.objects.filter(pk=self.manager.pk).update(
                    role="branch_manager", branch=self.branch
                )
            return original(klass, *args, **kwargs)

        with patch.object(business_views, "get_object_or_404", side_effect=demote):
            response = self.client.post(
                reverse("business_resource_add", args=["san-pham"]),
                {
                    "sku": "ESCALATED",
                    "name": "Unauthorized",
                    "unit": "chai",
                    "reorder_level": 2,
                    "active": "on",
                },
            )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Product.objects.filter(sku="ESCALATED").exists())

    def reset_with_concurrent_update(self, updates):
        user = self.manager
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        response = self.client.get(
            reverse("password_reset_confirm", kwargs={"uidb64": uid, "token": token})
        )
        target = response.url
        clean = SetPasswordForm.clean

        def update(form):
            result = clean(form)
            User.objects.filter(pk=user.pk).update(**updates)
            return result

        with patch.object(SetPasswordForm, "clean", update):
            response = self.client.post(
                target,
                {"new_password1": "Changed@Quality2026", "new_password2": "Changed@Quality2026"},
            )
        return response

    def test_reset_never_restores_stale_privileges_or_point_balance(self):
        self.reset_with_concurrent_update({"role": "customer", "points": 7})
        self.manager.refresh_from_db()
        self.assertEqual((self.manager.role, self.manager.points), ("customer", 7))
        self.assertTrue(self.manager.check_password("Changed@Quality2026"))

    def test_reset_rejects_an_account_disabled_after_token_validation(self):
        old = self.manager.password
        self.reset_with_concurrent_update({"is_active": False})
        self.manager.refresh_from_db()
        self.assertFalse(self.manager.is_active)
        self.assertEqual(self.manager.password, old)

    def test_branch_can_enroll_only_a_blank_local_guest_mailbox(self):
        self.customer.set_unusable_password()
        self.customer.save(update_fields=["password"])
        self.reserve()
        self.client.force_login(self.boss)
        self.client.post(
            reverse("business_customer_contact", args=[self.customer.pk]),
            {
                "full_name": self.customer.full_name,
                "phone": self.customer.phone,
                "email": "guest@example.test",
                "verified": "on",
            },
        )
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.email, "guest@example.test")
        self.client.post(
            reverse("business_customer_contact", args=[self.customer.pk]),
            {
                "full_name": self.customer.full_name,
                "phone": self.customer.phone,
                "email": "replacement@example.test",
                "verified": "on",
            },
        )
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.email, "guest@example.test")

    def test_branch_cannot_enroll_a_blank_guest_shared_with_another_branch(self):
        self.customer.set_unusable_password()
        self.customer.save(update_fields=["password"])
        self.reserve()
        self.reserve(
            branch_id=self.other_branch.pk,
            employee_id=self.other_employee.pk,
            start=local_at(self.day, time(12)),
        )
        self.client.force_login(self.boss)
        self.client.post(
            reverse("business_customer_contact", args=[self.customer.pk]),
            {
                "full_name": self.customer.full_name,
                "phone": self.customer.phone,
                "email": "attacker@example.test",
                "verified": "on",
            },
        )
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.email, "")

    def test_login_throttle_is_shared_across_clients_and_ignores_forwarded_ip(self):
        from django.test import Client

        url = reverse("login")
        for _ in range(10):
            self.assertEqual(
                Client().post(url, {"username": "not-real", "password": "wrong"}).status_code, 200
            )
        response = Client().post(
            url, {"username": " \tnot-real  ", "password": "wrong"}, HTTP_X_FORWARDED_FOR="8.8.8.8"
        )
        self.assertEqual(response.status_code, 429)
        self.assertIn("Retry-After", response)

    def test_sensitive_page_headers_and_telemetry_never_include_reset_token(self):
        self.client.force_login(self.customer)
        response = self.client.get(reverse("profile"))
        self.assertIn("no-store", response.headers.get("Cache-Control", ""))
        self.assertIn("script-src 'self'", response.headers.get("Content-Security-Policy", ""))
        self.assertEqual(len(response.headers.get("X-Request-ID", "")), 32)
        with self.assertLogs("gentleman.http", level="INFO") as logs:
            self.client.get("/dat-lai-mat-khau/abc/PRIVATE-RESET-TOKEN/?email=private@example.test")
        text = " ".join(logs.output)
        self.assertNotIn("PRIVATE-RESET-TOKEN", text)
        self.assertNotIn("private@example.test", text)

    def paid(self, start, points=0):
        a = self.reserve(start=start)
        a.status = "awaiting_payment"
        a.save()
        transition(pk=a.pk, actor=self.manager, action="pay", redeem_points=points)
        return a.invoice

    def test_refund_earn_then_redemption_does_not_create_phantom_debt(self):
        earn = self.paid(local_at(self.day, time(10)))
        redeem = self.paid(local_at(self.day, time(11)), 10)
        business.refund_invoice(actor=self.manager, invoice_id=earn.pk, reason="Hoàn A")
        business.refund_invoice(actor=self.manager, invoice_id=redeem.pk, reason="Hoàn B")
        self.customer.refresh_from_db()
        self.assertEqual((self.customer.points, self.customer.points_debt), (0, 0))
        self.paid(local_at(self.day, time(12)))
        self.customer.refresh_from_db()
        self.assertEqual((self.customer.points, self.customer.points_debt), (10, 0))

    def test_refund_reverse_order_preserves_same_entitlement(self):
        earn = self.paid(local_at(self.day, time(10)))
        redeem = self.paid(local_at(self.day, time(11)), 10)
        business.refund_invoice(actor=self.manager, invoice_id=redeem.pk, reason="Hoàn B")
        business.refund_invoice(actor=self.manager, invoice_id=earn.pk, reason="Hoàn A")
        self.customer.refresh_from_db()
        self.assertEqual((self.customer.points, self.customer.points_debt), (0, 0))


class QualityQueryBudgets(Fixtures, TestCase):
    @classmethod
    def setUpTestData(cls):
        Fixtures.make_data(cls)
        for n in range(10):
            b = Branch.objects.create(
                name=f"Quality {n}",
                address="Test",
                phone="0901234567",
                opens_at=time(9),
                closes_at=time(21),
            )
            e = Employee.objects.create(name=f"Stylist {n}", branch=b, specialty="Cắt")
            Chair.objects.create(branch=b, name="Ghế 1")
            Shift.objects.create(
                employee=e, start_at=local_at(cls.day, time(9)), end_at=local_at(cls.day, time(21))
            )

    def setUp(self):
        self.client.force_login(self.manager)

    def measured(self, name, params, budget):
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(reverse(name), params)
        self.assertEqual(response.status_code, 200)
        print(f"QUERY_BUDGET {name}: {len(queries)} queries / budget {budget}")
        self.assertLessEqual(len(queries), budget)

    def test_branch_overview_uses_grouped_reads_not_queries_per_branch(self):
        self.measured("business_board", {"date": str(self.day)}, 15)

    def test_resource_relations_are_loaded_together(self):
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(reverse("business_resources", args=["stylist"]))
        self.assertEqual(response.status_code, 200)
        print(f"QUERY_BUDGET stylist resources: {len(queries)} / 8")
        self.assertLessEqual(len(queries), 8)

    def test_daily_schedule_queries_do_not_grow_with_stylist_count(self):
        self.measured("schedule", {"date": str(self.day)}, 10)

    def test_appointment_history_is_bounded_and_actor_joined(self):
        a = self.reserve()
        for n in range(30):
            AppointmentChange.objects.create(
                appointment=a, actor=self.manager, action="test", reason=f"History {n}"
            )
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(reverse("appointment_detail", args=[a.pk]))
        self.assertEqual(response.status_code, 200)
        print(f"QUERY_BUDGET detail history: {len(queries)} / 12")
        self.assertLessEqual(len(queries), 12)


class AuthLimitConcurrencyTests(TransactionTestCase):
    def test_expired_limit_resets_and_expired_peer_keys_are_reaped(self):
        from salon.hardening import consume
        from salon.models import AuthRateBucket
        from django.utils import timezone

        self.assertTrue(consume("expiry", "known", 1, 60)[0])
        self.assertFalse(consume("expiry", "known", 1, 60)[0])
        AuthRateBucket.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertTrue(consume("expiry", "known", 1, 60)[0])
        AuthRateBucket.objects.create(
            key="a" * 64, count=2, expires_at=timezone.now() - timedelta(seconds=1)
        )
        self.assertTrue(consume("expiry", "new", 1, 60)[0])
        self.assertFalse(AuthRateBucket.objects.filter(key="a" * 64).exists())

    def test_parallel_connections_share_one_atomic_counter(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import connections
        from salon.hardening import consume
        from salon.models import AuthRateBucket

        barrier = Barrier(6)

        def attempt(_):
            try:
                barrier.wait(timeout=10)
                return consume("test-parallel", "sensitive@example.test", 3, 60)[0]
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(attempt, range(6)))
        self.assertEqual(sum(results), 3)
        bucket = AuthRateBucket.objects.get()
        self.assertEqual(bucket.count, 3)
        self.assertNotIn("sensitive", bucket.key)
