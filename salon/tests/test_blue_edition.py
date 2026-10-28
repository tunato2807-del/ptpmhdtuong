"""Privacy and pagination boundaries of the Blue Edition read models."""

from datetime import time
from django.test import TestCase
from django.urls import reverse
from salon.models import User
from salon.services import local_at
from .test_workflows import Fixtures


class BlueEditionReadTests(Fixtures, TestCase):
    @classmethod
    def setUpTestData(cls):
        Fixtures.make_data(cls)

    def test_profile_next_visit_belongs_only_to_signed_in_customer(self):
        mine = self.reserve(start=local_at(self.day, time(11)))
        other = User.objects.create_user(username="blue-other", role="customer")
        self.reserve(customer=other, start=local_at(self.day, time(10)))
        self.client.force_login(self.customer)
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.context["next_appointment"].pk, mine.pk)
        self.assertContains(response, mine.code)
        self.client.force_login(other)
        self.assertNotEqual(
            self.client.get(reverse("profile")).context["next_appointment"].pk, mine.pk
        )

    def test_branch_lanes_do_not_expose_other_branch_appointments(self):
        mine = self.reserve()
        self.reserve(
            customer=self.other_customer,
            branch_id=self.other_branch.pk,
            employee_id=self.other_employee.pk,
        )
        self.client.force_login(self.receptionist)
        response = self.client.get(reverse("business_board"), {"date": self.day})
        rows = response.context["branch_rows"]
        self.assertEqual([r["branch"].pk for r in rows], [self.branch.pk])
        self.assertEqual([a.pk for r in rows for a in r["appointments"]], [mine.pk])
        self.assertEqual(response.context["board_totals"]["bookings"], 1)

    def test_lane_filter_changes_visible_cards_without_changing_day_totals(self):
        self.reserve()
        self.client.force_login(self.manager)
        response = self.client.get(
            reverse("business_board"), {"date": self.day, "q": "no-such-person"}
        )
        self.assertEqual(response.context["page_obj"].paginator.count, 0)
        self.assertEqual(sum(len(r["appointments"]) for r in response.context["branch_rows"]), 0)
        self.assertEqual(response.context["board_totals"]["bookings"], 1)
