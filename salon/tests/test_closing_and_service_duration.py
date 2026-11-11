from datetime import time, timedelta
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from salon import business
from salon.models import DailyClosing, Service, Shift, User
from salon.services import local_at, transition
from .test_workflows import Fixtures


class ClosingAndServiceDurationTests(Fixtures, TestCase):
    @classmethod
    def setUpTestData(cls):
        Fixtures.make_data(cls)
        cls.boss = User.objects.create_user(
            username="branchboss", role="branch_manager", branch=cls.branch, full_name="Quản lý A"
        )
        cls.stylist_user = User.objects.create_user(
            username="stylistuser", role="stylist", branch=cls.branch, full_name="Stylist A"
        )
        cls.employee.account = cls.stylist_user
        cls.employee.save()

    def ready(self):
        a = self.reserve()
        a.start_at = local_at(timezone.localdate(), time(10))
        a.end_at = a.start_at + timedelta(minutes=30)
        a.save()
        with patch("salon.services.timezone.now", return_value=a.start_at):
            transition(pk=a.pk, actor=self.manager, action="checkin", chair_id=self.chair.pk)
            transition(pk=a.pk, actor=self.stylist_user, action="start")
        return a

    def test_saving_same_services_preserves_manual_extension(self):
        a = self.ready()
        extended = business.extend_service(
            actor=self.boss, pk=a.pk, minutes=30, reason="Khách cần thêm thời gian"
        )
        business.change_services(
            actor=self.boss, pk=a.pk, service_ids=[self.service.pk], reason="Khách xác nhận lại"
        )
        a.refresh_from_db()
        self.assertEqual(a.end_at, extended.end_at)
        change = a.changes.get(action="services")
        self.assertEqual(change.before["end"], change.after["end"])

    def test_adding_service_preserves_extension_and_existing_snapshots(self):
        a = self.ready()
        extended = business.extend_service(
            actor=self.boss, pk=a.pk, minutes=30, reason="Phục vụ kéo dài"
        )
        self.service.price = 300000
        self.service.duration = 60
        self.service.save()
        business.change_services(
            actor=self.boss,
            pk=a.pk,
            service_ids=[self.service.pk, self.second_service.pk],
            reason="Khách đồng ý thêm gội",
        )
        a.refresh_from_db()
        self.assertEqual(a.end_at, extended.end_at + timedelta(minutes=30))
        self.assertEqual(a.total, 180000)
        self.assertEqual(a.items.get(service=self.service).duration, 30)

    def test_removing_service_preserves_extension(self):
        a = self.ready()
        business.change_services(
            actor=self.boss,
            pk=a.pk,
            service_ids=[self.service.pk, self.second_service.pk],
            reason="Khách thêm gội",
        )
        extended = business.extend_service(
            actor=self.boss, pk=a.pk, minutes=30, reason="Cần thêm thời gian"
        )
        business.change_services(
            actor=self.boss, pk=a.pk, service_ids=[self.service.pk], reason="Khách bỏ gội"
        )
        a.refresh_from_db()
        self.assertEqual(a.end_at, extended.end_at - timedelta(minutes=30))
        self.assertEqual(a.total, 100000)
        self.assertFalse(a.items.filter(service=self.second_service).exists())

    def test_saving_services_preserves_late_checkin_allocation(self):
        today = timezone.localdate()
        with patch("salon.services.timezone.now", return_value=local_at(today, time(9))):
            a = self.reserve(start=local_at(today, time(10)))
        late_arrival = a.start_at + timedelta(minutes=20, seconds=30)
        with patch("salon.services.timezone.now", return_value=late_arrival):
            checked_in = transition(
                pk=a.pk,
                actor=self.receptionist,
                action="checkin",
                chair_id=self.chair.pk,
                reason="Khách đến muộn, đã điều phối",
            )
            business.change_services(
                actor=self.boss,
                pk=a.pk,
                service_ids=[self.service.pk],
                reason="Khách giữ dịch vụ cũ",
            )
        a.refresh_from_db()
        self.assertGreaterEqual(checked_in.end_at, late_arrival + timedelta(minutes=30))
        self.assertEqual(a.end_at, checked_in.end_at)

    def test_added_service_checks_conflicts_in_preserved_extension(self):
        a = self.ready()
        extended = business.extend_service(
            actor=self.boss, pk=a.pk, minutes=30, reason="Phục vụ kéo dài"
        )
        with patch("salon.services.timezone.now", return_value=a.start_at - timedelta(hours=1)):
            self.reserve(customer=self.other_customer, start=extended.end_at)
        before = business.snapshot(extended)
        changes = a.changes.count()
        with self.assertRaises(ValidationError):
            business.change_services(
                actor=self.boss,
                pk=a.pk,
                service_ids=[self.service.pk, self.second_service.pk],
                reason="Thêm gội sẽ lấn sang lịch kế tiếp",
            )
        a.refresh_from_db()
        self.assertEqual(business.snapshot(a), before)
        self.assertEqual(a.changes.count(), changes)

    def test_added_service_checks_customer_conflict_across_branches(self):
        a = self.ready()
        extended = business.extend_service(
            actor=self.boss, pk=a.pk, minutes=30, reason="Phục vụ kéo dài"
        )
        with patch("salon.services.timezone.now", return_value=a.start_at - timedelta(hours=1)):
            self.reserve(
                branch_id=self.other_branch.pk,
                employee_id=self.other_employee.pk,
                start=extended.end_at,
            )
        before = business.snapshot(extended)
        changes = a.changes.count()
        with self.assertRaisesMessage(ValidationError, "trùng lịch khác của khách"):
            business.change_services(
                actor=self.boss,
                pk=a.pk,
                service_ids=[self.service.pk, self.second_service.pk],
                reason="Khách muốn thêm gội",
            )
        a.refresh_from_db()
        self.assertEqual(business.snapshot(a), before)
        self.assertEqual(a.changes.count(), changes)

    def test_service_time_limit_includes_extension_and_accepts_exactly_eight_hours(self):
        a = self.ready()
        business.extend_service(actor=self.boss, pk=a.pk, minutes=60, reason="Cần thêm thời gian")
        self.second_service.duration = 240
        self.second_service.save()
        long_service = Service.objects.create(
            name="Chăm sóc chuyên sâu", price=200000, duration=180
        )
        selected = [self.second_service.pk, long_service.pk]
        business.change_services(
            actor=self.boss, pk=a.pk, service_ids=selected, reason="Khách đổi gói dịch vụ"
        )
        a.refresh_from_db()
        self.assertEqual(a.end_at - a.start_at, timedelta(minutes=480))
        before = business.snapshot(a)
        changes = a.changes.count()
        with self.assertRaisesMessage(ValidationError, "8 giờ"):
            business.change_services(
                actor=self.boss,
                pk=a.pk,
                service_ids=[*selected, self.service.pk],
                reason="Không được vượt tổng thời gian cho phép",
            )
        a.refresh_from_db()
        self.assertEqual(business.snapshot(a), before)
        self.assertEqual(a.changes.count(), changes)

    def test_closing_refuses_booked_and_keeps_day_open_for_service(self):
        today = timezone.localdate()
        with patch("salon.services.timezone.now", return_value=local_at(today, time(9))):
            a = self.reserve(start=local_at(today, time(10)))
            with self.assertRaises(ValidationError):
                business.close_day(
                    actor=self.boss, branch_id=self.branch.pk, day=today, counted=0, reason=""
                )
        self.assertFalse(DailyClosing.objects.filter(branch=self.branch, day=today).exists())
        with patch("salon.services.timezone.now", return_value=a.start_at):
            transition(pk=a.pk, actor=self.receptionist, action="checkin", chair_id=self.chair.pk)
            transition(pk=a.pk, actor=self.stylist_user, action="start")
            transition(pk=a.pk, actor=self.stylist_user, action="finish")
            transition(pk=a.pk, actor=self.receptionist, action="pay")
            closing = business.close_day(
                actor=self.boss, branch_id=self.branch.pk, day=today, counted=100000, reason=""
            )
        self.assertEqual(closing.invoices_count, 1)
        self.assertEqual(closing.expected_cash, 100000)

    def test_closing_refuses_unresolved_booked_from_previous_day(self):
        yesterday = timezone.localdate() - timedelta(days=1)
        Shift.objects.create(
            employee=self.employee,
            start_at=local_at(yesterday, time(9)),
            end_at=local_at(yesterday, time(21)),
        )
        with patch("salon.services.timezone.now", return_value=local_at(yesterday, time(9))):
            self.reserve(start=local_at(yesterday, time(10)))
        with self.assertRaises(ValidationError):
            business.close_day(
                actor=self.boss,
                branch_id=self.branch.pk,
                day=timezone.localdate(),
                counted=0,
                reason="",
            )
        self.assertFalse(DailyClosing.objects.exists())

    def test_closing_ignores_future_bookings_and_other_branch(self):
        self.reserve()
        today = timezone.localdate()
        with patch("salon.services.timezone.now", return_value=local_at(today, time(9))):
            self.reserve(
                customer=self.other_customer,
                branch_id=self.other_branch.pk,
                employee_id=self.other_employee.pk,
                start=local_at(today, time(10)),
            )
        closing = business.close_day(
            actor=self.boss, branch_id=self.branch.pk, day=today, counted=0, reason=""
        )
        self.assertEqual(closing.branch_id, self.branch.pk)
        self.assertFalse(DailyClosing.objects.filter(branch=self.other_branch).exists())

    def test_closing_allows_resolved_cancelled_and_no_show_bookings(self):
        today = timezone.localdate()
        with patch("salon.services.timezone.now", return_value=local_at(today, time(9))):
            cancelled = self.reserve(start=local_at(today, time(10)))
            no_show = self.reserve(customer=self.other_customer, start=cancelled.end_at)
            transition(pk=cancelled.pk, actor=self.receptionist, action="cancel")
        with patch("salon.services.timezone.now", return_value=local_at(today, time(12))):
            transition(pk=no_show.pk, actor=self.receptionist, action="no_show")
            closing = business.close_day(
                actor=self.boss, branch_id=self.branch.pk, day=today, counted=0, reason=""
            )
        self.assertEqual(closing.invoices_count, 0)

    def test_closing_page_explains_unresolved_bookings_without_closing_day(self):
        today = timezone.localdate()
        with patch("salon.services.timezone.now", return_value=local_at(today, time(9))):
            self.reserve(start=local_at(today, time(10)))
        self.client.force_login(self.boss)
        response = self.client.post(
            reverse("business_closing"),
            {"branch": self.branch.pk, "day": today.isoformat(), "counted": 0, "confirm": "on"},
        )
        self.assertContains(response, "Còn lịch đã đặt")
        self.assertFalse(DailyClosing.objects.exists())
