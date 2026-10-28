from unittest.mock import patch
from django.test import SimpleTestCase
from salon.checks import required_interface_assets


class InterfaceAssetChecksTests(SimpleTestCase):
    def test_complete_checkout_has_required_interface_files(self):
        self.assertEqual(required_interface_assets(None), [])

    def test_partial_copy_reports_exact_missing_stylesheet(self):
        def find_asset(name):
            return None if name == "css/management.css" else "/static/" + name

        with patch("salon.checks.finders.find", side_effect=find_asset):
            errors = required_interface_assets(None)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, "salon.E001")
        self.assertIn("static/css/management.css", errors[0].msg)


class TemplateInventoryTests(SimpleTestCase):
    def test_complete_checkout_compiles_every_required_template(self):
        from salon.checks import required_interface_templates

        self.assertEqual(required_interface_templates(None), [])

    def test_missing_shared_feature_template_reports_exact_local_path(self):
        from django.template import TemplateDoesNotExist
        from django.template.loader import get_template
        from salon.checks import required_interface_templates

        def load(name):
            if name == "features/page.html":
                raise TemplateDoesNotExist(name)
            return get_template(name)

        with patch("django.template.loader.get_template", side_effect=load):
            errors = required_interface_templates(None)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, "salon.E002")
        self.assertIn("features/page.html", errors[0].hint)

    def test_bad_template_syntax_has_an_actionable_check(self):
        from django.template import TemplateSyntaxError
        from django.template.loader import get_template
        from salon.checks import required_interface_templates

        def load(name):
            if name == "features/reports.html":
                raise TemplateSyntaxError("Invalid block tag")
            return get_template(name)

        with patch("django.template.loader.get_template", side_effect=load):
            errors = required_interface_templates(None)
        self.assertEqual(errors[0].id, "salon.E003")
