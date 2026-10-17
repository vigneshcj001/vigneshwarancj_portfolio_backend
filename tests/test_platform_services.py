import unittest

from pydantic import ValidationError

from app.schemas.platform import EventPayload
from app.services.demos import simulate_project


class PlatformServiceTests(unittest.TestCase):
    def test_sensitive_pocketpet_action_requires_approval(self):
        result = simulate_project("pocketpet", "Purchase this product")
        self.assertEqual(result["action"], "approval_required")

    def test_aiora_booking_uses_booking_route(self):
        result = simulate_project("aiora", "Book an appointment")
        self.assertEqual(result["route"], "booking")

    def test_analytics_rejects_personal_properties(self):
        with self.assertRaises(ValidationError):
            EventPayload(name="contact_success", properties={"email": "private@example.com"})


if __name__ == "__main__":
    unittest.main()
