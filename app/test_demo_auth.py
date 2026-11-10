import hashlib
import json
import sys
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request,urlopen
from pathlib import Path
import server
import test_learning as fixtures
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'maintenance'))
import demo_auth

class DemoAuthTest(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.LearningTest();self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        demo_auth.ensure_schema()
        self.http=None
        self.start_http()
        self.addCleanup(self.stop_http)

    def start_http(self,handler=demo_auth.DemoHandler):
        self.http=ThreadingHTTPServer(('127.0.0.1',0),handler)
        self.thread=threading.Thread(target=self.http.serve_forever,daemon=True);self.thread.start()
        self.base='http://127.0.0.1:'+str(self.http.server_port)

    def stop_http(self):
        if self.http:
            self.http.shutdown();self.http.server_close();self.thread.join();self.http=None

    def request(self,path,body=None,token='',cookie=False):
        headers={'Content-Type':'application/json'}
        if token:headers['Cookie' if cookie else 'Authorization']=('ege_session=' if cookie else 'Bearer ')+token
        with urlopen(Request(self.base+path,data=None if body is None else json.dumps(body).encode(),headers=headers)) as response:return json.load(response)

    def test_demo_sessions_survive_restart_and_keep_roles(self):
        tokens={role:self.request('/api/login',{'username':role,'password':role+'123'})['token'] for role in ['student','teacher']}
        with server.db() as con:
            stored={r[0] for r in con.execute('SELECT token_hash FROM local_demo_sessions')}
        self.assertEqual(stored,{hashlib.sha256(t.encode()).hexdigest() for t in tokens.values()})
        self.stop_http();server.SESSIONS.clear();self.start_http()
        for role,token in tokens.items():
            self.assertEqual(self.request('/api/me',token=token)['user']['role'],role)
            self.assertEqual(self.request('/api/me',token=token,cookie=True)['user']['role'],role)
            self.assertTrue(self.request('/api/activities',token=token)['activities'])
        self.assertIsNone(self.request('/api/me',token='invalid')['user'])
        self.request('/api/logout',{},token=tokens['student'])
        server.SESSIONS.clear()
        self.assertIsNone(self.request('/api/me',token=tokens['student'])['user'])
        self.assertEqual(self.request('/api/me',token=tokens['teacher'])['user']['role'],'teacher')

    def test_main_application_does_not_restore_demo_sessions(self):
        token=self.request('/api/login',{'username':'student','password':'student123'})['token']
        self.stop_http();server.SESSIONS.clear();self.start_http(server.Handler)
        self.assertIsNone(self.request('/api/me',token=token)['user'])

if __name__=='__main__':unittest.main()
