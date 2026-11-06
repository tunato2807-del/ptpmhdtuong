"""Counting records must not certify unverified rows or fabricate missing ones."""

from contextlib import redirect_stdout
from io import StringIO
import json
from django.apps import apps
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from salon.models import User


class DataTargetAuditTests(TestCase):
    def test_reports_counts_and_deficits_without_rows_or_false_verification(self):
        User.objects.create_user(username="audit-owner", full_name="PRIVATE FIXTURE NAME")
        output = StringIO()
        call_command("audit_data_targets", target=100, stdout=output)
        text = output.getvalue()
        report = json.loads(text)
        self.assertEqual(
            len(report["tables"]), len(list(apps.get_app_config("salon").get_models()))
        )
        users = next(t for t in report["tables"] if t["model"] == "User")
        self.assertEqual(users["row_count"], 1)
        self.assertEqual(users["shortfall_to_count_target"], 99)
        self.assertIsNone(users["verified_real_rows"])
        self.assertFalse(users["public_source_candidate"])
        self.assertNotIn("PRIVATE FIXTURE NAME", text)
        self.assertNotIn("audit-owner", text)
        self.assertEqual(User.objects.count(), 1)

    def test_invalid_target_is_rejected(self):
        for target in (0, -1, 1001):
            with self.subTest(target=target), self.assertRaises(CommandError):
                call_command("audit_data_targets", target=target, stdout=StringIO())
