"""Local browser fixture; never uses the application's real database."""
import json
import sys
import threading
from pathlib import Path
from http.server import ThreadingHTTPServer
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from test_statistics import StatisticsTest
import server
import learning_module
import statistics_module

case=StatisticsTest();case.setUp()
for n in range(130):
    case.add_attempt('ege10' if n%2 else 'ege9',n%3==0,prompt=f'История решения {n}: проверка гласной')
case.add_attempt(prompt='Самая старая ошибка: л..сной',created='2026-01-01T12:00:00+00:00')
for n in range(5):case.add_attempt('ege12',True,prompt=f'Уверенная тема {n}')
learning_module.game_result(server,case.student,{'slug':'autumn-leaves','event_id':'qa-wrong-game','is_correct':False,'prompt':'ц..плёнок','given_answer':'и','correct_answer':'ы'})
learning_module.game_result(server,case.student,{'slug':'participle-map','event_id':'qa-old-game','is_correct':False,'prompt':'identify: legacy-task'})
empty={**case.student,'user_id':'stats-empty-student','username':'stats-empty-student','email':'stats-empty@example.test','display_name':'Ученик без решений'}
with server.db() as con:
    columns=list(empty)
    con.execute('INSERT INTO users('+','.join(columns)+') VALUES('+','.join('?' for _ in columns)+')',[empty[k] for k in columns])
    con.execute("UPDATE attempts SET rule_name='Уверенная тема',rule_id='qa-strong' WHERE prompt LIKE 'Уверенная тема%'")
con.close()
test=case.case.create({'activity':'ege9','mode':'line','count':2})
letter_test=case.case.create({'activity':'ege9','mode':'line','count':2,'require_letters':True})
letter_snap=case.case.snapshots(letter_test['id'])[0]
letter_ids=[w for row in letter_snap['question']['row_word_ids'] for w in row]
row_test=case.case.create({'activity':'ege11','mode':'line','count':1})
snap=case.case.snapshots(row_test['id'])[0]
row_given='15' if snap['question']['correct_answer'] != '15' else '1'
learning_module.check_question(server,case.student,{'test_id':row_test['id'],
    'question_id':snap['question_id'],'answer':row_given})
fixture={'student_id':case.student['user_id'],'empty_id':empty['user_id'],'test_id':test['id'],
         'letter_test_id':letter_test['id'],'letter_key':letter_snap['question']['correct_answer'],
         'letters':{str(i):server.WORD_BY_ID[w]['correct_letter'] for i,w in enumerate(letter_ids)},
         'row_key':snap['question']['correct_answer'],'row_given':row_given,
         'summary':statistics_module.overview(server,case.student)['summary'],'database':str(case.case.path)}
qa=Path(__file__).resolve().parent/'offline-qa';qa.mkdir(exist_ok=True)
(qa/'statistics-fixtures.json').write_text(json.dumps(fixture,ensure_ascii=False),encoding='utf-8')

class Handler(server.Handler):
    def do_POST(self):
        if self.path == '/qa/shutdown' and self.client_address[0] == '127.0.0.1':
            self.send_json({'ok':True});threading.Thread(target=self.server.shutdown,daemon=True).start()
        else:super().do_POST()

http=ThreadingHTTPServer(('127.0.0.1',8098),Handler)
server.configure_console();print('Statistics QA http://127.0.0.1:8098',flush=True)
try:http.serve_forever()
finally:http.server_close();case.doCleanups()
