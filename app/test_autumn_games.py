import json
import re
import threading
import unittest
from contextlib import nullcontext
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import urlopen

import server


class AutumnGamesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.visit_patch = patch.object(server, 'record_public_game_visit')
        cls.visit_patch.start()
        cls.http = ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        cls.thread = threading.Thread(target=cls.http.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.http.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown()
        cls.http.server_close()
        cls.thread.join()
        cls.visit_patch.stop()

    def get(self, path):
        return urlopen(self.base + quote(path, safe='/:?='))

    def test_herbarium_limits_apply_to_every_web_entry(self):
        original = (server.HTML_GAMES['autumn-herbarium'] / 'index.html').read_text(encoding='utf-8')
        for prefix in ('games', 'html-games', 'Full-64093178520648-autumn-herbarium'):
            path = f'/{prefix}/autumn-herbarium/index.html' if prefix in ('games', 'html-games') else f'/{prefix}/index.html'
            with self.get(path) as response:
                html = response.read().decode('utf-8')
            data = json.loads(re.search(r'id="gameData">(.*?)</script>', html, re.S)[1])
            self.assertTrue(all(0 < len(t['items']) <= 50 for t in data['topics']))
            self.assertNotIn('value="all"', html)
            self.assertNotIn('fileInput', html)
            self.assertNotIn('settingsDialog', html)
            self.assertIn('Случайные 12', html)
            self.assertIn('Случайные 24', html)
            # Exact preservation of the game's stylesheet and animation definitions.
            self.assertEqual(re.search(r'<style>(.*?)</style>', original, re.S)[1], re.search(r'<style>(.*?)</style>', html, re.S)[1].replace('\r\n', '\n'))

    def test_offline_download_preserves_full_features(self):
        with self.get('/Full-64093178520648-autumn-herbarium/offline.html') as response:
            html = response.read()
            self.assertIn('attachment', response.headers['Content-Disposition'])
        source = server.HTML_GAMES['autumn-herbarium'] / 'index.html'
        self.assertEqual(html, source.read_bytes())
        self.assertIn(b'fileInput', html)
        self.assertIn(b'value="all"', html)

    def test_public_routes_do_not_expose_full_database_or_answers(self):
        for path in ('/games/autumn-herbarium/offline.html', '/html-games/autumn-herbarium/Ответы (вся база).pdf', '/full-games/autumn-herbarium/index.html'):
            with self.assertRaises(HTTPError) as error:
                self.get(path)
            self.assertEqual(error.exception.code, 404)

    def test_mini_entry_alias_and_download(self):
        for path in ('/games/autumn-leaves/index.html', '/games/autumn-leaves/autumn.html', '/html-games/autumn-leaves/index.html', '/Full-79328410563827-autumn-leaves/offline.html'):
            with self.get(path) as response:
                self.assertIn(b'loadTeacherSet()', response.read())

    def test_constructor_accepts_multiple_letters_and_word_options(self):
        payload = server.normalize_game_payload({'title': 'Другие орфограммы', 'mechanic': 'autumn-leaves', 'items': [
            {'variant': 'з..ря', 'answer': 'а', 'options': ['а', 'о']},
            {'variant': '..правда', 'answer': 'не', 'options': ['не', '-']},
            {'variant': 'дли..ый', 'answer': 'нн', 'options': ['н', 'нн']},
        ]})
        self.assertEqual(payload['items'][2]['options'], ['н', 'нн'])
        self.assertEqual(payload['items'][0]['answer'], 'а')
        self.assertIn('autumn-leaves', server.GAME_MECHANICS)
        with self.assertRaises(ValueError):
            server.normalize_game_payload({'title': 'Ошибка', 'mechanic': 'autumn-leaves', 'items': [{'variant': 'слово', 'answer': 'один', 'options': ['один']}]})

    def test_constructor_builds_rounds_from_each_compatible_base(self):
        catalog = server.game_sources_for_teacher()
        mechanic = next(m for m in catalog['mechanics'] if m['id'] == 'autumn-leaves')
        for source in catalog['sources']:
            self.assertIn(source['id'], mechanic['compatible_sources'])
            rule = next(r for rules in source['rules'].values() for r in rules if r['mechanic_counts']['autumn-leaves'])
            with patch.object(server, 'db', return_value=nullcontext(None)), patch.object(server, 'save_game_set', side_effect=lambda con, user, payload, source: payload):
                game = server.create_game_set_from_base({'role': 'teacher'}, {'mechanic': 'autumn-leaves', 'source': source['id'], 'rule_ids': [rule['rule_id']], 'count': 3})
            self.assertEqual(game['mechanic'], 'autumn-leaves')
            self.assertTrue(game['items'])
            self.assertTrue(all(len(item['options']) >= 2 for item in game['items']))

    def test_shop_prices_and_delivery_are_wired(self):
        for slug, amount in [('autumn-leaves', '200.00'), ('autumn-herbarium', '400.00')]:
            product = server.SHOP_PRODUCTS[slug]
            self.assertEqual(product['amount'], amount)
            self.assertTrue(product['default_url'].endswith('/offline.html'))
            self.assertTrue(product['online_url'].endswith('/index.html'))
            self.assertTrue(server.product_email_note(product))


if __name__ == '__main__':
    unittest.main()
