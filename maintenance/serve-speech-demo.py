"""Run the actual application against an isolated demo database."""
import os
import sys
from pathlib import Path
from http.server import ThreadingHTTPServer
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'app'))
os.environ['SEED_DEMO_USERS']='1'
import server
import ege_speech_engine
import demo_auth
server.DATA_DIR=ROOT/'data'/'speech-demo'
server.DATA_DIR.mkdir(parents=True,exist_ok=True)
path=server.DATA_DIR/'ege_app.db'
for name in ['server','ege1_3_module','ege5_module','ege10_module','ege11_module','ege12_module','ege13_module','ege14_module','ege15_module','ege_speech_engine']:
    sys.modules[name].DB_PATH=path
server.ensure_app_db()
demo_auth.ensure_schema()
with server.db() as con:
    for user in con.execute("SELECT user_id FROM users WHERE username IN ('student','teacher')").fetchall():
        server.insert_user_consent(con,user['user_id'],'127.0.0.1','Local demo')
if '--open-browser' in sys.argv:
    import threading,webbrowser
    threading.Timer(1,lambda:webbrowser.open('http://127.0.0.1:8090/demo.html')).start()
print('Demo: http://127.0.0.1:8090/demo.html',flush=True)
ThreadingHTTPServer(('127.0.0.1',8090),demo_auth.DemoHandler).serve_forever()
