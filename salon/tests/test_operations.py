from datetime import timedelta
from io import BytesIO
import re
from unittest.mock import patch
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from openpyxl import load_workbook
from salon.models import Notification, AuditLog, PointEntry, Invoice, Appointment
from salon.services import transition
from .test_workflows import Fixtures


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class PasswordRecoveryTests(Fixtures, TestCase):
    def setUp(self):
        self.make_data()
        cache.clear()
        self.customer.email = "owner@example.com"
        self.customer.save(update_fields=["email"])

    def test_full_reset_flow_rejects_bad_password_and_reused_token(self):
        response = self.client.post(reverse("password_reset"), {"email": self.customer.email})
        self.assertRedirects(response, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        link = re.search(r"http://testserver([^\s]+)", mail.outbox[0].body).group(1)
        response = self.client.get(link)
        change_url = response.url
        self.assertEqual(self.client.get(change_url).status_code, 200)
        response = self.client.post(change_url, {"new_password1": "x", "new_password2": "y"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        response = self.client.post(
            change_url, {"new_password1": "Fresh@Reset2026", "new_password2": "Fresh@Reset2026"}
        )
        self.assertRedirects(response, reverse("password_reset_complete"))
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.check_password("Fresh@Reset2026"))
        self.assertContains(self.client.get(link), "không hợp lệ")

    def test_unknown_inactive_and_unusable_users_receive_same_generic_response(self):
        self.customer.is_active = False
        self.customer.save(update_fields=["is_active"])
        self.other_customer.email = "unusable@example.com"
        self.other_customer.set_unusable_password()
        self.other_customer.save()
        for email in ["missing@example.com", self.customer.email, self.other_customer.email]:
            response = self.client.post(reverse("password_reset"), {"email": email}, follow=True)
            self.assertContains(response, "Nếu email thuộc tài khoản")
        self.assertEqual(len(mail.outbox), 0)

    def test_reset_post_csrf_throttle_and_expired_links(self):
        self.assertEqual(
            Client(enforce_csrf_checks=True)
            .post(reverse("password_reset"), {"email": self.customer.email})
            .status_code,
            403,
        )
        for _ in range(3):
            self.client.post(reverse("password_reset"), {"email": self.customer.email})
        self.assertEqual(len(mail.outbox), 1)
        token = default_token_generator.make_token(self.customer)
        uid = urlsafe_base64_encode(force_bytes(self.customer.pk))
        with patch.object(
            default_token_generator,
            "_now",
            return_value=default_token_generator._now() + timedelta(hours=2),
        ):
            response = self.client.get(reverse("password_reset_confirm", args=[uid, token]))
        self.assertContains(response, "hết hạn")


class OperationsTests(Fixtures, TestCase):
    def setUp(self):
        self.make_data()
        self.booking = self.reserve()
        self.client.force_login(self.customer)

    def test_notification_has_booking_link_and_read_is_owned_post_only(self):
        item = Notification.objects.get(recipient=self.customer)
        self.assertEqual(item.appointment_id, self.booking.pk)
        self.assertContains(self.client.get(reverse("notifications")), "Xem lịch hẹn")
        self.assertEqual(
            self.client.get(reverse("notification_read", args=[item.pk])).status_code, 405
        )
        self.client.force_login(self.other_customer)
        self.assertEqual(
            self.client.post(reverse("notification_read", args=[item.pk])).status_code, 404
        )
        self.client.force_login(self.customer)
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.customer)
        self.assertEqual(csrf.post(reverse("notification_read", args=[item.pk])).status_code, 403)
        self.client.post(reverse("notification_read", args=[item.pk]))
        item.refresh_from_db()
        self.assertIsNotNone(item.read_at)
        self.assertEqual(
            self.client.get(reverse("notifications"), {"state": "unread"})
            .context["page_obj"]
            .paginator.count,
            0,
        )

    def test_mark_all_does_not_change_another_user_notifications(self):
        own = Notification.objects.create(recipient=self.customer, message="Riêng tư")
        other = Notification.objects.create(recipient=self.other_customer, message="Khách khác")
        self.client.post(reverse("notifications_read_all"))
        own.refresh_from_db()
        other.refresh_from_db()
        self.assertIsNotNone(own.read_at)
        self.assertIsNone(other.read_at)

    def test_notification_filters_and_pagination(self):
        Notification.objects.bulk_create(
            [Notification(recipient=self.customer, message=f"Mới {i}") for i in range(25)]
        )
        response = self.client.get(reverse("notifications"), {"per_page": "10", "page": "2"})
        self.assertEqual(len(response.context["page_obj"]), 10)
        self.assertEqual(response.context["unread_count"], 26)
        self.assertEqual(
            self.client.get(reverse("notifications"), {"state": "read"})
            .context["page_obj"]
            .paginator.count,
            0,
        )

    def test_audit_is_manager_only_searchable_and_not_editable(self):
        for user in [self.customer, self.receptionist]:
            self.client.force_login(user)
            self.assertEqual(self.client.get(reverse("audit")).status_code, 403)
        self.client.force_login(self.manager)
        AuditLog.objects.create(
            actor=self.manager, appointment=self.booking, action="Thay đổi thử nghiệm"
        )
        response = self.client.get(
            reverse("audit"), {"q": self.booking.code, "actor": self.manager.username}
        )
        self.assertEqual(response.context["page_obj"].paginator.count, 1)
        self.assertContains(response, "Thay đổi thử nghiệm")
        self.assertEqual(self.client.post(reverse("audit"), {}).status_code, 405)
        response = self.client.get(reverse("audit"), {"start": "bad-date"})
        self.assertTrue(response.context["form"].errors)

    def test_week_is_scoped_keeps_filters_and_handles_invalid_dates(self):
        other = self.reserve(
            customer=self.other_customer,
            branch_id=self.other_branch.pk,
            employee_id=self.other_employee.pk,
        )
        self.assertEqual(self.client.get(reverse("week")).status_code, 403)
        self.client.force_login(self.receptionist)
        response = self.client.get(
            reverse("week"), {"date": str(self.day), "employee": self.employee.pk}
        )
        self.assertEqual(len(response.context["days"]), 7)
        self.assertContains(response, self.booking.customer.full_name)
        self.assertNotContains(response, self.other_customer.full_name)
        self.assertIn("employee=", response.context["next_query"])
        response = self.client.get(
            reverse("week"), {"date": str(self.day), "branch": self.other_branch.pk}
        )
        self.assertTrue(response.context["form"].errors)
        for value in ["0001-01-01", "9999-12-31", "bad"]:
            response = self.client.get(reverse("week"), {"date": value})
            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.context["days"])

    def test_performance_scoped_revenue_allocations_and_export(self):
        a = self.booking
        a.status = "completed"
        a.save()
        Invoice.objects.create(
            appointment=a,
            total=80000,
            discount=20000,
            points_used=20,
            method="cash",
            cashier=self.manager,
        )
        b = self.reserve(
            customer=self.other_customer,
            branch_id=self.other_branch.pk,
            employee_id=self.other_employee.pk,
        )
        b.status = "completed"
        b.save()
        Invoice.objects.create(appointment=b, total=100000, method="cash", cashier=self.manager)
        cancelled = self.reserve(start=self.booking.end_at)
        cancelled.status = "cancelled"
        cancelled.save()
        self.client.force_login(self.receptionist)
        response = self.client.get(
            reverse("performance"), {"start": str(timezone.localdate()), "end": str(self.day)}
        )
        self.assertEqual(response.context["revenue"], 80000)
        self.assertEqual(sum(r["total"] for r in response.context["services"]), 80000)
        self.assertEqual(sum(r["total"] for r in response.context["stylists"]), 80000)
        self.assertEqual(response.context["cancel_rate"], 50)
        export = self.client.get(reverse("performance_export", args=["xlsx"]))
        self.assertEqual(export.status_code, 200)
        book = load_workbook(BytesIO(export.content))
        self.assertEqual(book.active["A1"].value, "Nhóm")
        self.assertEqual(
            self.client.get(reverse("performance_export", args=["pdf"])).status_code, 200
        )
        response = self.client.get(reverse("performance"), {"branch": self.other_branch.pk})
        self.assertTrue(response.context["invalid"])
        self.assertEqual(
            self.client.get(
                reverse("performance_export", args=["xlsx"]), {"branch": self.other_branch.pk}
            ).status_code,
            400,
        )

    def test_points_history_is_personal_and_cannot_be_edited(self):
        PointEntry.objects.create(customer=self.customer, kind="opening", amount=10, balance=10)
        response = self.client.get(reverse("points"))
        self.assertEqual(response.context["page_obj"].paginator.count, 1)
        self.client.force_login(self.other_customer)
        self.assertEqual(self.client.get(reverse("points")).context["page_obj"].paginator.count, 0)
        self.assertEqual(self.client.post(reverse("points"), {"points": 999}).status_code, 405)


class LoyaltyTests(Fixtures, TestCase):
    def setUp(self):
        self.make_data()
        self.customer.points = 50
        self.customer.save(update_fields=["points"])
        self.booking = self.reserve()
        self.booking.status = "awaiting_payment"
        self.booking.save()

    def pay(self, points):
        return transition(
            pk=self.booking.pk, actor=self.manager, action="pay", redeem_points=points
        )

    def test_checkout_uses_old_points_and_earns_only_on_net_with_ledger(self):
        self.pay(20)
        invoice = Invoice.objects.get(appointment=self.booking)
        self.assertEqual(
            (invoice.subtotal, invoice.discount, invoice.total, invoice.points_used),
            (100000, 20000, 80000, 20),
        )
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.points, 38)
        entries = list(
            PointEntry.objects.filter(customer=self.customer)
            .order_by("pk")
            .values_list("kind", "amount", "balance")
        )
        self.assertEqual(entries, [("opening", 50, 50), ("redeemed", -20, 30), ("earned", 8, 38)])
        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            self.pay(20)
        self.assertEqual(Invoice.objects.filter(appointment=self.booking).count(), 1)
        self.assertEqual(PointEntry.objects.filter(invoice=invoice).count(), 2)

    def test_invalid_insufficient_and_over_limit_points_rollback_payment(self):
        from django.core.exceptions import ValidationError

        for value in [-1, "2", True, 21, 51]:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                self.pay(value)
        self.assertFalse(Invoice.objects.filter(appointment=self.booking).exists())
        self.assertFalse(PointEntry.objects.filter(customer=self.customer).exists())
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.points, 50)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, "awaiting_payment")

    def test_database_rejects_inconsistent_discount_and_negative_earned_points(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Invoice.objects.create(
                appointment=self.booking,
                total=90000,
                discount=10000,
                points_used=0,
                method="cash",
                cashier=self.manager,
            )
        with self.assertRaises(IntegrityError), transaction.atomic():
            PointEntry.objects.create(customer=self.customer, kind="earned", amount=-1, balance=50)

    def test_checkout_form_and_pdf_show_discount_and_total(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("appointment_detail", args=[self.booking.pk]))
        self.assertContains(response, "redeem_points")
        self.client.post(
            reverse("appointment_action", args=[self.booking.pk]),
            {"action": "pay", "redeem_points": "20"},
        )
        response = self.client.get(reverse("invoice", args=[self.booking.pk]))
        self.assertContains(response, "80.000")
        self.assertContains(response, "20.000")
        self.assertEqual(
            self.client.get(reverse("feature_invoice_pdf", args=[self.booking.pk])).status_code, 200
        )


from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from django.db import close_old_connections, connections
from django.test import TransactionTestCase


class ConcurrentPointsTests(Fixtures, TransactionTestCase):
    def test_two_branches_cannot_spend_the_same_points(self):
        self.make_data()
        self.customer.points = 20
        self.customer.save(update_fields=["points"])
        first = self.reserve()
        second = self.reserve(
            branch_id=self.other_branch.pk,
            employee_id=self.other_employee.pk,
            start=first.start_at + timedelta(hours=1),
        )
        Appointment.objects.filter(pk__in=[first.pk, second.pk]).update(status="awaiting_payment")
        gate = Barrier(2)

        def pay(pk):
            from django.core.exceptions import ValidationError

            close_old_connections()
            try:
                gate.wait(timeout=10)
                transition(pk=pk, actor=self.manager, action="pay", redeem_points=20)
                return "paid"
            except ValidationError:
                return "insufficient"
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            result = list(pool.map(pay, [first.pk, second.pk]))
        self.assertCountEqual(result, ["paid", "insufficient"])
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.points, 8)
        self.assertEqual(Invoice.objects.count(), 1)
        self.assertEqual(PointEntry.objects.filter(kind="redeemed").count(), 1)
