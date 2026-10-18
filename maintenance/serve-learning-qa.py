import sys
from pathlib import Path
from http.server import ThreadingHTTPServer
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
from test_learning import LearningTest
import server
import json
import learning_module
server.configure_console()
case = LearningTest()
case.setUp()
fixtures = []
for activity, mode in [('ege5','paronym_exam'),('ege9','line'),('ege10','line'),('ege11','line'),('ege12','line'),
                       ('ege13','line_ne'),('ege14','exam'),('ege14','line_spelling'),('ege15','sentence_nn')]:
    test = case.create({'activity':activity,'mode':mode,'count':1})
    snap = case.snapshots(test['id'])[0]
    answer = snap['question']['correct_answer']
    if snap['question']['kind'] == 'paronym_exam':
        row,word = answer.split('|',1)
        answer = {'row':row,'word':word}
    elif snap['question']['kind'] == 'ege14_line':
        answer = {'mode':answer,'words':snap['question']['word_answers']}
    fixtures.append({'test_id':test['id'],'activity':activity,'mode':mode,'answer':answer})
fixture_path = Path(__file__).resolve().parent/'offline-qa'/'learning-fixtures.json'
fixture_path.parent.mkdir(exist_ok=True)
fixture_path.write_text(json.dumps(fixtures,ensure_ascii=False),encoding='utf-8')
http = ThreadingHTTPServer(('127.0.0.1', 8097), server.Handler)
print('Learning QA http://127.0.0.1:8097', flush=True)
try:
    http.serve_forever()
finally:
    http.server_close()
    case.doCleanups()
