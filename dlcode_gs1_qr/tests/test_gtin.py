from odoo.tests.common import BaseCase

from ..models.gtin import valid_gtin


class TestGtin(BaseCase):
    def test_valid_gtin(self):
        self.assertEqual(valid_gtin("4006381333931"), "04006381333931")
        self.assertEqual(valid_gtin("036000291452"), "00036000291452")
        self.assertEqual(valid_gtin("96385074"), "00000096385074")
        self.assertIsNone(valid_gtin("4006381333932"))
        self.assertIsNone(valid_gtin("12345"))
        self.assertIsNone(valid_gtin(False))
