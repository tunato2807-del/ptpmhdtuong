from datetime import timedelta, time
from django.test import TestCase, Client
from django.urls import reverse
from salon.forms import ShiftForm
from salon.models import User, Branch, Service, Employee, Chair, Shift, Appointment, AuditLog
from salon.services import local_at
from .test_workflows import Fixtures


class ManagementTests(Fixtures, TestCase):
    def setUp(self):
        self.make_data()
        self.client.force_login(self.manager)

    def url(self, key, action="list", pk=None):
        kwargs = {"resource": key}
        if pk is not None:
            kwargs["pk"] = pk
        return reverse("resource_" + action, kwargs=kwargs)

    def test_no_django_admin_and_custom_pages_use_role_instead_of_staff_flags(self):
        self.manager.is_superuser = False
        self.manager.is_staff = False
        self.manager.save()
        self.assertEqual(self.client.get("/admin/").status_code, 404)
        response = self.client.get(reverse("settings"))
        self.assertContains(response, "Thiết lập & nhân sự")
        self.assertNotContains(response, "/admin/")
        for key in ["dich-vu", "chi-nhanh", "stylist", "ghe", "ca-lam", "tai-khoan"]:
            self.assertEqual(self.client.get(self.url(key)).status_code, 200)
            self.assertEqual(self.client.get(self.url(key, "create")).status_code, 200)
        self.assertEqual(self.client.get(self.url("khong-co")).status_code, 404)

    def test_all_management_routes_reject_customers_and_receptionists(self):
        objects = {
            "dich-vu": self.service,
            "chi-nhanh": self.branch,
            "stylist": self.employee,
            "ghe": self.chair,
            "ca-lam": Shift.objects.first(),
            "tai-khoan": self.customer,
        }
        for user in [self.customer, self.receptionist]:
            self.client.force_login(user)
            self.assertEqual(self.client.get(reverse("settings")).status_code, 403)
            for key, obj in objects.items():
                for action, pk in [
                    ("list", None),
                    ("create", None),
                    ("edit", obj.pk),
                    ("delete", obj.pk),
                ]:
                    with self.subTest(user=user.role, key=key, action=action):
                        url = self.url(key, action, pk)
                        self.assertEqual(self.client.get(url).status_code, 403)
                        self.assertEqual(self.client.post(url, {"confirm": "on"}).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(reverse("settings")).status_code, 302)

    def test_create_edit_delete_all_six_resource_types(self):
        start = local_at(self.day + timedelta(days=2), time(9))
        end = start + timedelta(hours=8)
        cases = [
            (
                "dich-vu",
                Service,
                {
                    "name": "Mới",
                    "kind": "hair",
                    "description": "Mô tả",
                    "price": 110000,
                    "duration": 30,
                    "active": "on",
                },
                "name",
                "Đã sửa",
            ),
            (
                "chi-nhanh",
                Branch,
                {
                    "name": "Mới",
                    "address": "Hồ Chí Minh",
                    "phone": "0901111222",
                    "opens_at": "09:00",
                    "closes_at": "21:00",
                    "active": "on",
                },
                "name",
                "Đã sửa",
            ),
            (
                "stylist",
                Employee,
                {
                    "name": "Mới",
                    "branch": self.branch.pk,
                    "specialty": "Fade",
                    "bio": "Tận tâm",
                    "active": "on",
                },
                "name",
                "Đã sửa",
            ),
            (
                "ghe",
                Chair,
                {"name": "Mới", "branch": self.branch.pk, "active": "on"},
                "name",
                "Đã sửa",
            ),
            (
                "ca-lam",
                Shift,
                {
                    "employee": self.employee.pk,
                    "start_at": start.isoformat(),
                    "end_at": end.isoformat(),
                },
                "end_at",
                (end - timedelta(hours=1)).isoformat(),
            ),
            (
                "tai-khoan",
                User,
                {
                    "username": "new-manager-test",
                    "full_name": "Mới",
                    "phone": "0901111222",
                    "email": "new@example.com",
                    "role": "customer",
                    "is_active": "on",
                    "new_password": "New@Password27",
                },
                "full_name",
                "Đã sửa",
            ),
        ]
        for key, model, payload, field, value in cases:
            with self.subTest(resource=key):
                response = self.client.post(self.url(key, "create"), payload)
                self.assertEqual(
                    response.status_code, 302, response.context and response.context["form"].errors
                )
                obj = model.objects.latest("pk")
                if model is User:
                    self.assertTrue(obj.check_password("New@Password27"))
                    self.assertFalse(obj.is_superuser)
                payload[field] = value
                if model is User:
                    payload["new_password"] = ""
                self.assertEqual(
                    self.client.post(self.url(key, "edit", obj.pk), payload).status_code, 302
                )
                obj.refresh_from_db()
                if field != "end_at":
                    self.assertEqual(getattr(obj, field), value)
                else:
                    self.assertEqual(obj.end_at, end - timedelta(hours=1))
                self.assertEqual(self.client.get(self.url(key, "delete", obj.pk)).status_code, 200)
                self.assertTrue(model.objects.filter(pk=obj.pk).exists())
                self.assertEqual(
                    self.client.post(self.url(key, "delete", obj.pk), {}).status_code, 200
                )
                self.assertTrue(model.objects.filter(pk=obj.pk).exists())
                self.assertEqual(
                    self.client.post(
                        self.url(key, "delete", obj.pk), {"confirm": "on"}
                    ).status_code,
                    302,
                )
                self.assertFalse(model.objects.filter(pk=obj.pk).exists())
        self.assertEqual(AuditLog.objects.filter(actor=self.manager).count(), 18)

    def test_protected_service_cannot_be_deleted_and_snapshots_survive_edits(self):
        appointment = self.reserve()
        response = self.client.post(
            self.url("dich-vu", "delete", self.service.pk), {"confirm": "on"}
        )
        self.assertContains(response, "không thể xóa")
        payload = {
            "name": "Giá mới",
            "price": 300000,
            "duration": 60,
            "kind": "hair",
            "active": "on",
        }
        self.assertEqual(
            self.client.post(self.url("dich-vu", "edit", self.service.pk), payload).status_code, 302
        )
        appointment.refresh_from_db()
        self.assertEqual(appointment.total, 100000)
        self.assertEqual(appointment.end_at - appointment.start_at, timedelta(minutes=30))

    def test_shift_deletion_and_shrinking_cannot_break_existing_booking(self):
        self.reserve()
        shift = Shift.objects.get(employee=self.employee, start_at__date=self.day)
        response = self.client.post(self.url("ca-lam", "delete", shift.pk), {"confirm": "on"})
        self.assertContains(response, "Không thể xóa ca này")
        response = self.client.post(
            self.url("ca-lam", "edit", shift.pk),
            {
                "employee": self.employee.pk,
                "start_at": local_at(self.day, time(11)).isoformat(),
                "end_at": shift.end_at.isoformat(),
            },
        )
        self.assertContains(response, "Không được thay đổi ca làm")
        shift.refresh_from_db()
        self.assertEqual(timezone_local_hour(shift.start_at), 9)

    def test_branch_hours_and_deactivation_keep_scheduled_coverage(self):
        self.reserve()
        payload = {
            "name": self.branch.name,
            "address": self.branch.address,
            "phone": self.branch.phone,
            "opens_at": "09:00",
            "closes_at": "21:00",
        }
        response = self.client.post(self.url("chi-nhanh", "edit", self.branch.pk), payload)
        self.assertContains(response, "Chi nhánh còn lịch hẹn")
        payload.update(active="on", opens_at="10:00")
        response = self.client.post(self.url("chi-nhanh", "edit", self.branch.pk), payload)
        self.assertContains(response, "điều chỉnh các ca làm")
        self.branch.refresh_from_db()
        self.assertTrue(self.branch.active)
        self.assertEqual(self.branch.opens_at, time(9))

    def test_employee_and_chair_cannot_move_branches_by_post_tampering(self):
        for key, obj, payload in [
            (
                "stylist",
                self.employee,
                {
                    "name": "Stylist A",
                    "branch": self.other_branch.pk,
                    "specialty": "Layer",
                    "active": "on",
                },
            ),
            ("ghe", self.chair, {"name": "Ghế 01", "branch": self.other_branch.pk, "active": "on"}),
        ]:
            self.assertEqual(
                self.client.post(self.url(key, "edit", obj.pk), payload).status_code, 302
            )
            obj.refresh_from_db()
            self.assertEqual(obj.branch_id, self.branch.pk)

    def test_busy_employee_and_chair_cannot_be_disabled(self):
        appointment = self.reserve()
        appointment.chair = self.chair
        appointment.status = "checked_in"
        appointment.save()
        for key, obj, payload in [
            (
                "stylist",
                self.employee,
                {"name": "Stylist A", "branch": self.branch.pk, "specialty": "Fade"},
            ),
            ("ghe", self.chair, {"name": self.chair.name, "branch": self.branch.pk}),
        ]:
            response = self.client.post(self.url(key, "edit", obj.pk), payload)
            self.assertEqual(response.status_code, 200)
            obj.refresh_from_db()
            self.assertTrue(obj.active)

    def test_self_lock_role_change_and_delete_are_blocked(self):
        payload = {
            "username": self.manager.username,
            "full_name": "Quản trị",
            "role": "customer",
            "email": "m@example.com",
        }
        self.assertEqual(
            self.client.post(self.url("tai-khoan", "edit", self.manager.pk), payload).status_code,
            302,
        )
        self.manager.refresh_from_db()
        self.assertEqual(self.manager.role, "manager")
        self.assertTrue(self.manager.is_active)
        response = self.client.post(
            self.url("tai-khoan", "delete", self.manager.pk), {"confirm": "on"}
        )
        self.assertContains(response, "không thể xóa tài khoản đang đăng nhập")
        self.assertTrue(User.objects.filter(pk=self.manager.pk).exists())

    def test_account_validation_branch_password_hash_and_hidden_fields(self):
        payload = {
            "username": "new-staff",
            "full_name": "Nhân viên",
            "role": "receptionist",
            "is_active": "on",
            "new_password": "New@Password27",
        }
        response = self.client.post(self.url("tai-khoan", "create"), payload)
        self.assertContains(response, "Lễ tân cần một chi nhánh")
        payload.update(branch=self.branch.pk, new_password="123", is_superuser="on", points=999)
        self.assertEqual(
            self.client.post(self.url("tai-khoan", "create"), payload).status_code, 200
        )
        self.assertFalse(User.objects.filter(username="new-staff").exists())
        payload["new_password"] = "New@Password27"
        self.assertEqual(
            self.client.post(self.url("tai-khoan", "create"), payload).status_code, 302
        )
        user = User.objects.get(username="new-staff")
        self.assertTrue(user.check_password(payload["new_password"]))
        self.assertFalse(user.is_superuser)
        self.assertEqual(user.points, 0)

    def test_customer_with_history_cannot_be_converted_to_staff(self):
        self.reserve()
        response = self.client.post(
            self.url("tai-khoan", "edit", self.customer.pk),
            {
                "username": self.customer.username,
                "full_name": self.customer.full_name,
                "role": "manager",
                "is_active": "on",
            },
        )
        self.assertContains(response, "Khách đã có lịch hẹn")
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.role, "customer")

    def test_duplicate_and_invalid_shift_are_rejected(self):
        shift = Shift.objects.get(employee=self.employee, start_at__date=self.day)
        self.assertEqual(
            self.client.post(
                self.url("ca-lam", "create"),
                {
                    "employee": self.employee.pk,
                    "start_at": shift.start_at.isoformat(),
                    "end_at": shift.end_at.isoformat(),
                },
            ).status_code,
            200,
        )
        self.assertFalse(
            ShiftForm(
                data={
                    "employee": self.employee.pk,
                    "start_at": shift.end_at,
                    "end_at": shift.start_at,
                }
            ).is_valid()
        )

    def test_mutations_require_csrf_and_unaccepted_methods_are_rejected(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.manager)
        self.assertEqual(
            client.post(
                self.url("dich-vu", "delete", self.service.pk), {"confirm": "on"}
            ).status_code,
            403,
        )
        self.assertEqual(client.post(self.url("dich-vu", "create"), {"name": "x"}).status_code, 403)
        self.assertEqual(
            self.client.delete(self.url("dich-vu", "delete", self.service.pk)).status_code, 405
        )
        self.assertEqual(self.client.post(self.url("dich-vu")).status_code, 405)


class ProfileTests(Fixtures, TestCase):
    def setUp(self):
        self.make_data()
        self.client.force_login(self.customer)

    def test_profile_requires_login_and_is_available_for_all_roles(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("profile")).status_code, 302)
        for user in [self.customer, self.receptionist, self.manager]:
            self.client.force_login(user)
            self.assertContains(self.client.get(reverse("profile")), user.full_name)

    def test_profile_changes_only_own_contact_information(self):
        self.customer.points = 42
        self.customer.save()
        password = self.customer.password
        response = self.client.post(
            reverse("profile"),
            {
                "action": "profile",
                "full_name": "Tên mới",
                "phone": "0901111222",
                "email": "updated@example.com",
                "pk": self.manager.pk,
                "role": "manager",
                "points": 999,
                "is_superuser": "on",
                "username": "hacked",
                "password": "plaintext",
            },
        )
        self.assertRedirects(response, reverse("profile"))
        self.customer.refresh_from_db()
        self.manager.refresh_from_db()
        self.assertEqual(self.customer.full_name, "Tên mới")
        self.assertEqual(self.customer.email, "updated@example.com")
        self.assertEqual(self.customer.role, "customer")
        self.assertEqual(self.customer.points, 42)
        self.assertEqual(self.customer.username, "customer")
        self.assertEqual(self.customer.password, password)
        self.assertFalse(self.customer.is_superuser)
        self.assertNotEqual(self.manager.full_name, "Tên mới")

    def test_invalid_contact_information_does_not_save(self):
        response = self.client.post(
            reverse("profile"),
            {"action": "profile", "full_name": "Tên mới", "phone": "abc", "email": "bad"},
        )
        self.assertEqual(response.status_code, 200)
        self.customer.refresh_from_db()
        self.assertNotEqual(self.customer.full_name, "Tên mới")

    def test_password_requires_current_password_and_retains_current_session(self):
        response = self.client.post(
            reverse("profile"),
            {
                "action": "password",
                "old_password": "wrong",
                "new_password1": "Fresh@Password27",
                "new_password2": "Fresh@Password27",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.check_password("Test@Password26"))
        response = self.client.post(
            reverse("profile"),
            {
                "action": "password",
                "old_password": "Test@Password26",
                "new_password1": "Fresh@Password27",
                "new_password2": "Fresh@Password27",
            },
        )
        self.assertRedirects(response, reverse("profile"))
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.check_password("Fresh@Password27"))
        self.assertEqual(self.client.get(reverse("my_appointments")).status_code, 200)
        other = Client()
        self.assertFalse(other.login(username=self.customer.username, password="Test@Password26"))
        self.assertTrue(other.login(username=self.customer.username, password="Fresh@Password27"))

    def test_unknown_action_and_missing_csrf_are_rejected(self):
        self.assertEqual(
            self.client.post(reverse("profile"), {"action": "role", "role": "manager"}).status_code,
            400,
        )
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.customer)
        self.assertEqual(client.post(reverse("profile"), {"action": "profile"}).status_code, 403)


def timezone_local_hour(value):
    from django.utils import timezone

    return timezone.localtime(value).hour
