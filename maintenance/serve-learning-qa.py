import sys
from pathlib import Path
from http.server import ThreadingHTTPServer
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
from test_learning import LearningTest
import server
server.configure_console()
case = LearningTest()
case.setUp()
http = ThreadingHTTPServer(('127.0.0.1', 8097), server.Handler)
print('Learning QA http://127.0.0.1:8097', flush=True)
try:
    http.serve_forever()
finally:
    http.server_close()
    case.doCleanups()
