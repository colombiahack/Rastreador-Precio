import unittest

from pricewatch.db import DB
from pricewatch.detector import detect
from pricewatch.models import Item
from pricewatch.scrapers.base import parse_cop


def mk(price, lp=None):
    return Item("T", "1", "TV 55", "http://x", price, lp)


class DetectorTests(unittest.TestCase):
    def test_drop_vs_history(self):
        g = detect(mk(500_000), 2_000_000)
        self.assertIsNotNone(g)
        self.assertEqual(g.drop_pct, 75.0)

    def test_no_alert_small_drop(self):
        self.assertIsNone(detect(mk(1_700_000), 2_000_000))

    def test_list_price_rule(self):
        self.assertIsNotNone(detect(mk(300_000, 1_500_000), None))

    def test_ignores_cheap_and_broken(self):
        self.assertIsNone(detect(mk(500), 100_000))       # precio roto
        self.assertIsNone(detect(mk(5_000), 20_000))      # referencia barata

    def test_baseline_needs_history(self):
        db = DB(":memory:")
        for p in (100_000, 110_000):
            db.save(mk(p))
        self.assertIsNone(db.baseline("T", "1"))
        db.save(mk(105_000))
        self.assertEqual(db.baseline("T", "1"), 105_000)

    def test_dedupe(self):
        db = DB(":memory:")
        it = mk(1)
        self.assertFalse(db.already_alerted(it))
        db.mark_alerted(it)
        self.assertTrue(db.already_alerted(it))


class ParseTests(unittest.TestCase):
    def test_parse_cop(self):
        self.assertEqual(parse_cop("1.299.900"), 1299900)
        self.assertEqual(parse_cop("$ 1.299.900,00"), 1299900)
        self.assertEqual(parse_cop(1299900), 1299900)
        self.assertIsNone(parse_cop("n/a"))


if __name__ == "__main__":
    unittest.main()
