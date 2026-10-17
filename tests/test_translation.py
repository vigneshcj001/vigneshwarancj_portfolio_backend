import unittest

from pydantic import ValidationError

from app.schemas.translation import TranslationRequest
from app.services.translation import normalize_translations


class TranslationTests(unittest.TestCase):
    def test_parses_ordered_json_response(self):
        result = normalize_translations('{"translations":["Bonjour","Projets"]}', 2)
        self.assertEqual(result, ["Bonjour", "Projets"])

    def test_rejects_wrong_translation_count(self):
        with self.assertRaises(ValueError):
            normalize_translations('{"translations":["Bonjour"]}', 2)

    def test_rejects_unsupported_language(self):
        with self.assertRaises(ValidationError):
            TranslationRequest(language="de", texts=["Home"])


if __name__ == "__main__":
    unittest.main()
