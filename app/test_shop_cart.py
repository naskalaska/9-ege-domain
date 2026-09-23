import gc
import sqlite3
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

import server


class ShopCartTest(unittest.TestCase):
    def setUp(self):
        self.original_db_path = server.DB_PATH
        self.test_db_path = Path(__file__).parent / "test_data" / f"shop-cart-{uuid.uuid4().hex}.db"
        server.DB_PATH = self.test_db_path
        server.ensure_app_db()

    def tearDown(self):
        server.DB_PATH = self.original_db_path
        gc.collect()
        for suffix in ("", "-wal", "-shm"):
            Path(f"{self.test_db_path}{suffix}").unlink(missing_ok=True)

    def test_participle_map_is_seeded_at_600(self):
        product = server.product_by_slug("participle-map")
        self.assertEqual(product["amount"], "600.00")
        self.assertEqual(product["id"], "participle_map")
        self.assertIn("/full-games/participle-map/", product["online_url"])
        self.assertTrue(product["delivery_url"].endswith("otvety-karta-prichastie-v35.pdf"))

    def test_cart_creates_one_payment_with_itemized_receipt(self):
        captured = {}

        def fake_payment(_shop_id, _secret_key, product, order_uid, email):
            captured.update(product=product, order_uid=order_uid, email=email)
            return {"id": "payment-test", "confirmation": {"confirmation_url": "https://pay.test/one"}}

        with patch.object(server, "yookassa_env", return_value=("shop", "secret", "url")), patch.object(
            server, "create_yookassa_payment", side_effect=fake_payment
        ):
            result = server.create_product_payment(
                {"email": "teacher@example.ru", "products": ["participle-map", "syntactic-soup"]}
            )

        self.assertEqual(result["confirmation_url"], "https://pay.test/one")
        self.assertEqual(captured["product"]["amount"], "900.00")
        self.assertEqual(len(captured["product"]["items"]), 2)
        with sqlite3.connect(self.test_db_path) as con:
            item_count = con.execute(
                "SELECT COUNT(*) FROM shop_order_items WHERE order_uid = ?", (captured["order_uid"],)
            ).fetchone()[0]
            order_count = con.execute("SELECT COUNT(*) FROM shop_orders").fetchone()[0]
            con.execute("UPDATE shop_orders SET status = 'paid' WHERE order_uid = ?", (captured["order_uid"],))
        self.assertEqual(order_count, 1)
        self.assertEqual(item_count, 2)
        self.assertTrue(
            server.user_can_access_full_game(
                {"role": "teacher", "email": "teacher@example.ru", "user_id": "teacher-test"},
                "syntactic-soup",
            )
        )

    def test_public_demo_injection_adds_30_action_guard(self):
        source = (Path(__file__).parent / "HTML" / "Карта причастия" / "karta-prichastie-v36.html").read_bytes()
        demo = server.inject_participle_map_demo(source, 30)
        self.assertIn(b"const demoLimit=30", demo)
        self.assertIn(b"if(!demoActionAllowed())return", demo)
        self.assertEqual(demo.count(b"function demoActionAllowed()"), 1)

    def test_game_source_contains_mobile_support(self):
        game_dir = Path(__file__).parent / "HTML" / "Карта причастия"
        source = (game_dir / "karta-prichastie-v36.html").read_bytes()
        mobile_css = (game_dir / "mobile-fixes.css").read_bytes()
        self.assertIn(b'href="mobile-fixes.css"', source)
        self.assertIn(b"viewport-fit=cover", source)
        self.assertNotIn(b"user-scalable=no", source)
        self.assertIn(b"min-width: 0 !important", mobile_css)
        self.assertIn(b"grid-template-columns: repeat(2, minmax(0, 1fr))", mobile_css)

    def test_participle_map_uses_normative_kolyushchiy(self):
        source = (
            Path(__file__).parent / "HTML" / "Карта причастия" / "karta-prichastie-v36.html"
        ).read_text(encoding="utf-8")
        self.assertNotIn("колущий", source.lower())
        self.assertGreaterEqual(source.lower().count("колющий"), 4)
        self.assertIn("['колющий','колют']", source)
        self.assertIn("['кол…щий','Ю']", source)
        self.assertNotIn("['кол…щий','У']", source)
        for fragment, vowel in (
            ("вед…щий", "У"), ("бор…щийся", "Ю"), ("дыш…щий", "А"), ("стро…щий", "Я"),
            ("чита…мый", "Е"), ("вид…мый", "И"), ("рису…щий", "Ю"), ("держ…щий", "А"),
            ("кле…щий", "Я"), ("реша…мый", "Е"), ("слыш…мый", "И"), ("пиш…щий", "У"),
            ("вою…щий", "Ю"), ("спеш…щий", "А"), ("завис…щий", "Я"), ("создава…мый", "Е"),
            ("хран…мый", "И"), ("ищ…щий", "У"), ("танцу…щий", "Ю"), ("крич…щий", "А"),
            ("лет…щий", "Я"), ("управля…мый", "Е"), ("гон…мый", "И"),
        ):
            self.assertIn(f"['{fragment}','{vowel}']", source)


if __name__ == "__main__":
    unittest.main()
