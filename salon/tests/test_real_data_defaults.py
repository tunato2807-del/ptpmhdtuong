"""Real-data setups must not silently create synthetic business records."""

from contextlib import redirect_stdout
from io import StringIO
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase, override_settings
from salon.models import User
from django.urls import reverse
from scripts import dev


class RealDataDefaultsTests(SimpleTestCase):
    def test_setup_never_seeds_even_with_legacy_demo_environment(self):
        for args in (["dev", "setup"], ["dev", "setup", "--no-demo"]):
            with self.subTest(args=args), TemporaryDirectory() as folder:
                root = Path(folder)
                (root / ".env").write_bytes(b"existing configuration sentinel")
                with (
                    patch.object(dev, "ROOT", root),
                    patch.object(dev, "PYTHON", Path(sys.executable)),
                    patch.object(dev, "run") as run,
                    patch("sys.argv", args),
                    patch.dict(os.environ, {"LOAD_DEMO_DATA": "1"}),
                    redirect_stdout(StringIO()),
                ):
                    self.assertEqual(dev.main(), 0)
                invoked = [call.args for call in run.call_args_list]
                self.assertNotIn(("manage.py", "seed_demo"), invoked)
                self.assertIn(("manage.py", "migrate", "--noinput"), invoked)
                self.assertEqual((root / ".env").read_bytes(), b"existing configuration sentinel")

    @override_settings(DEBUG=True)
    def test_login_does_not_advertise_shared_demo_passwords(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Gentleman@2026")
        self.assertNotContains(response, "Tài khoản trình diễn đồ án")


class RealManagerBootstrapTests(TestCase):
    def create_owner(self, passwords):
        with (
            patch("salon.management.commands.create_manager.sys.stdin.isatty", return_value=True),
            patch("salon.management.commands.create_manager.getpass", side_effect=passwords),
        ):
            call_command(
                "create_manager",
                username="owner",
                full_name="Người quản lý",
                email="owner@example.test",
                stdout=StringIO(),
            )

    def test_creates_manager_with_entered_identity_and_hashed_password(self):
        password = "Owner@Run2026!Strong"
        self.create_owner([password, password])
        user = User.objects.get(username="owner")
        self.assertEqual(user.full_name, "Người quản lý")
        self.assertEqual(user.email, "owner@example.test")
        self.assertEqual(user.role, User.Role.MANAGER)
        self.assertTrue(user.check_password(password))
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_staff)

    def test_existing_customer_is_never_promoted_or_overwritten(self):
        user = User.objects.create_user(username="owner", full_name="Chủ hồ sơ", role="customer")
        with self.assertRaises(CommandError):
            self.create_owner([])
        user.refresh_from_db()
        self.assertEqual(user.role, "customer")
        self.assertEqual(user.full_name, "Chủ hồ sơ")

    def test_weak_password_does_not_create_account(self):
        with self.assertRaises(CommandError):
            self.create_owner(["123", "123"])
        self.assertFalse(User.objects.filter(username="owner").exists())
