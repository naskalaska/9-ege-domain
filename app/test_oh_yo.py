import sys,threading,unittest
from pathlib import Path
from unittest.mock import patch
from urllib.request import urlopen
from urllib.error import HTTPError
from urllib.parse import quote,urlparse
from http.server import ThreadingHTTPServer
import server

class OhYoIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.visit=patch.object(server,'record_public_game_visit');cls.visit.start()
        cls.http=ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True);cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.http.server_port}'
    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown();cls.http.server_close();cls.thread.join();cls.visit.stop()
    def get(self,path):return urlopen(self.base+quote(path,safe='/:'))
    def test_entries_and_images(self):
        source=server.game_entry_file('oh-yo','index.html')
        for prefix in ['games','html-games']:
            for name in ['index.html',source]:
                with self.get(f'/{prefix}/oh-yo/{name}') as r:
                    self.assertIn('Вспомнить правило с Баюном',r.read().decode())
        for image in server.HTML_GAMES['oh-yo'].glob('*.png'):
            with self.get('/games/oh-yo/'+image.name) as r:
                self.assertEqual(r.headers['Content-Type'],'image/png');self.assertTrue(r.read().startswith(b'\x89PNG'))
    def test_purchase_delivery(self):
        product=server.SHOP_PRODUCTS['oh-yo']
        self.assertEqual(product['amount'],'400.00');self.assertEqual(product['kind'],'product')
        for key in ['default_url','online_url']:server.validate_delivery_link(product[key])
        with self.get(urlparse(product['default_url']).path) as r:
            self.assertIn('attachment',r.headers['Content-Disposition'])
            self.assertEqual(r.read(),(server.HTML_GAMES['oh-yo']/server.game_entry_file('oh-yo','index.html')).read_bytes())
        self.assertIn('интернет и установка не нужны',server.product_email_note(product))
    def test_public_download_alias_is_not_exposed(self):
        for prefix in ['games','html-games','full-games']:
            with self.assertRaises(HTTPError) as error:self.get(f'/{prefix}/oh-yo/offline.html')
            self.assertEqual(error.exception.code,404)

if __name__=='__main__':unittest.main()
