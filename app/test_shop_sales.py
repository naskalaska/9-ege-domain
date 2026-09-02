import gc
import sqlite3
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import server


class ShopSaleTest(unittest.TestCase):
    def setUp(self):
        self.original_db_path = server.DB_PATH
        self.test_db_path = Path(__file__).parent / "test_data" / f"shop-sale-{uuid.uuid4().hex}.db"
        server.DB_PATH = self.test_db_path
        server.ensure_app_db()
        self.admin = {"role": "admin"}

    def tearDown(self):
        server.DB_PATH = self.original_db_path
        gc.collect()
        for suffix in ("", "-wal", "-shm"):
            Path(f"{self.test_db_path}{suffix}").unlink(missing_ok=True)

    def test_active_sale_reaches_public_catalog_and_payment_product(self):
        sale_ends_at = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
        server.update_paid_entity(
            self.admin,
            {
                "product_id": "syntactic_soup",
                "title": "HTML-игра «Синтаксический суп»",
                "amount": "300",
                "sale_amount": "199",
                "sale_ends_at": sale_ends_at,
                "currency": "RUB",
                "cover_url": "/games/syntactic-soup/sintaksicheskiy-sup-cover.png",
                "delivery_url": "https://example.test/material",
                "online_url": "/full-games/syntactic-soup/index.html",
            },
        )

        public_product = next(
            item for item in server.shop_products_public()["products"]
            if item["slug"] == "syntactic-soup"
        )
        payment_product = server.product_by_slug("syntactic-soup")

        self.assertTrue(public_product["sale_active"])
        self.assertEqual(public_product["price"], "199 ₽")
        self.assertEqual(public_product["old_price"], "300 ₽")
        self.assertEqual(payment_product["amount"], "199.00")

    def test_expired_sale_falls_back_to_regular_price(self):
        with sqlite3.connect(server.DB_PATH) as con:
            con.execute(
                "UPDATE paid_entities SET sale_amount = ?, sale_ends_at = ? WHERE product_id = ?",
                (
                    "199.00",
                    (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
                    "syntactic_soup",
                ),
            )

        public_product = next(
            item for item in server.shop_products_public()["products"]
            if item["slug"] == "syntactic-soup"
        )
        payment_product = server.product_by_slug("syntactic-soup")

        self.assertFalse(public_product["sale_active"])
        self.assertEqual(public_product["price"], "300 ₽")
        self.assertEqual(public_product["old_price"], "")
        self.assertEqual(payment_product["amount"], "300.00")

    def test_sale_price_must_be_lower_than_regular_price(self):
        with self.assertRaisesRegex(ValueError, "ниже обычной"):
            server.normalize_sale_fields(
                "300.00",
                "300",
                (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
            )


if __name__ == "__main__":
    unittest.main()
