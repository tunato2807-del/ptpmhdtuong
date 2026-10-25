from unittest.mock import patch
from django.test import SimpleTestCase
from salon.checks import required_interface_assets


class InterfaceAssetChecksTests(SimpleTestCase):
    def test_complete_checkout_has_required_interface_files(self):
        self.assertEqual(required_interface_assets(None), [])

    def test_partial_copy_reports_exact_missing_stylesheet(self):
        def find_asset(name):
            return None if name == 'css/management.css' else '/static/' + name
        with patch('salon.checks.finders.find', side_effect=find_asset):
            errors = required_interface_assets(None)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, 'salon.E001')
        self.assertIn('static/css/management.css', errors[0].msg)
