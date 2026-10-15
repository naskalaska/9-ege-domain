import sys
from pathlib import Path
from http.server import ThreadingHTTPServer
sys.path.insert(0,str(Path('app').resolve()))
import server
server.DB_PATH=Path('maintenance/oh-yo-qa.db').resolve()
server.ensure_app_db()
server.record_public_game_visit=lambda *args:None
print('QA server ready',flush=True)
ThreadingHTTPServer(('127.0.0.1',8096),server.Handler).serve_forever()
