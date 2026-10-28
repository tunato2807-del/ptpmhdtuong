from django.test import TestCase,override_settings
from django.core.cache import cache
from django.core import mail
from django.urls import reverse
from salon.models import User

@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class WalkInActivationTests(TestCase):
    def setUp(self):cache.clear()
    def test_unusable_walkin_receives_link_and_remains_customer(self):
        user=User.objects.create(username='guest',role='customer',email='customer@example.com');user.set_unusable_password();user.save()
        response=self.client.post(reverse('activate_walkin'),{'email':user.email})
        self.assertEqual(response.status_code,302);self.assertEqual(len(mail.outbox),1)
        self.assertIn('/dat-lai-mat-khau/',mail.outbox[0].body)
        user.refresh_from_db();self.assertEqual(user.role,'customer');self.assertFalse(user.has_usable_password())
    def test_unknown_and_staff_addresses_get_generic_response_without_mail(self):
        User.objects.create(username='staff',role='receptionist',email='staff@example.com')
        for email in ('unknown@example.com','staff@example.com'):
            self.assertEqual(self.client.post(reverse('activate_walkin'),{'email':email}).status_code,302)
        self.assertEqual(len(mail.outbox),0)
    def test_existing_usable_password_is_not_changed_by_activation(self):
        user=User.objects.create_user(username='existing',email='customer@example.com',password='Secure@Password2026')
        self.client.post(reverse('activate_walkin'),{'email':user.email})
        self.assertEqual(len(mail.outbox),0);user.refresh_from_db();self.assertTrue(user.check_password('Secure@Password2026'))
