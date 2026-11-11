import io
import unittest
from unittest.mock import Mock, patch

import server
import test_shop_cart as fixtures


class EspressoRoutesTest(unittest.TestCase):
    def handler(self, path):
        handler = object.__new__(server.Handler)
        handler.path = path
        handler.wfile = io.BytesIO()
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()
        handler.send_json = Mock()
        return handler

    def test_public_routes_serve_only_one_pack_and_block_full_source(self):
        for method in ('send_public_game_file', 'send_html_game_file'):
            handler = self.handler('/games/espresso-murder/index.html')
            with patch.object(server, 'record_public_game_visit'):
                getattr(handler, method)('espresso-murder', 'index.html')
            body = handler.wfile.getvalue()
            self.assertIn(b"espresso-basic-user-source-v4", body)
            self.assertNotIn(b"espresso-expanded-user-source-v4", body)
            for filename in ('Расширенная версия.html', '%D0%A0%D0%B0%D1%81%D1%88%D0%B8%D1%80%D0%B5%D0%BD%D0%BD%D0%B0%D1%8F%20%D0%B2%D0%B5%D1%80%D1%81%D0%B8%D1%8F.html', '../Расширенная версия.html', 'Расширенная игра — 5 комплектов.html'):
                blocked = self.handler('/games/espresso-murder/' + filename)
                getattr(blocked, method)('espresso-murder', filename)
                blocked.send_json.assert_called_once()
                self.assertEqual(blocked.send_json.call_args.args[1], 404)

    def test_full_route_requires_numeric_key_and_serves_five_packs(self):
        blocked = self.handler('/full-games/espresso-murder/index.html')
        blocked.send_full_game_file('espresso-murder', 'index.html')
        self.assertEqual(blocked.send_json.call_args.args[1], 404)
        token = server.FULL_GAME_ROUTE_TOKENS['espresso-murder']
        self.assertRegex(token, r'^\d{14}$')
        self.assertEqual(server.PROTECTED_FULL_GAME_ROUTES[f'Full-{token}-espresso-murder'], 'espresso-murder')
        handler = self.handler(f'/Full-{token}-espresso-murder/index.html')
        handler.send_full_game_file('espresso-murder', 'index.html', protected_route=True)
        self.assertIn(b'espresso-expanded-user-source-v4', handler.wfile.getvalue())
        server.validate_delivery_link(server.SHOP_PRODUCTS['espresso-murder']['default_url'])

    def test_all_four_product_images_are_public(self):
        for name in ('01-oblozhka.png', '02-funkcional.png', '03-komplekt.png', '04-pyat-komplektov.png'):
            handler = self.handler('/games/espresso-murder/' + name)
            handler.send_public_game_file('espresso-murder', name)
            handler.send_response.assert_called_once_with(200)
            self.assertTrue(handler.wfile.getvalue().startswith(b'\x89PNG'))


class EspressoCheckoutTest(unittest.TestCase):
    setUp = fixtures.ShopCartTest.setUp
    tearDown = fixtures.ShopCartTest.tearDown

    def test_single_and_cart_receipts_use_price_and_paid_delivery_snapshot(self):
        # Exercise the actual receipt builder, with only the gateway mocked.
        for request, total, count in (({'product': 'espresso-murder'}, '300.00', 1),
                                      ({'products': ['espresso-murder', 'syntactic-soup']}, '600.00', 2)):
            with patch.object(server, 'yookassa_env', return_value=('shop', 'secret', 'url')), patch.object(
                server, 'yookassa_api_request', return_value={'id': 'espresso-test', 'confirmation': {'confirmation_url': 'https://pay.test'}}
            ) as gateway:
                server.create_product_payment({'email': 'teacher@example.ru', **request})
            payload = gateway.call_args.args[3]
            self.assertEqual(payload['amount']['value'], total)
            self.assertEqual(payload['receipt']['customer']['email'], 'teacher@example.ru')
            self.assertEqual(len(payload['receipt']['items']), count)
            self.assertEqual(payload['receipt']['items'][0]['amount']['value'], '300.00')
            self.assertEqual(payload['receipt']['items'][0]['description'], server.SHOP_PRODUCTS['espresso-murder']['title'])
        with server.db() as con:
            snapshots = con.execute("SELECT snapshot_json FROM shop_order_items WHERE product_id='espresso_murder'").fetchall()
        self.assertEqual(len(snapshots), 2)
        for row in snapshots:
            self.assertIn('/Full-94602718350964-espresso-murder/index.html', row[0])


if __name__ == '__main__':
    unittest.main()
