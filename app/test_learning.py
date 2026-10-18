import json
import random
import re
import subprocess
import tempfile
import threading
import gc
import uuid
import shutil
import unittest
from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from unittest.mock import patch

import server
import learning_module as learning
import game_tracking


class LearningTest(unittest.TestCase):
    def setUp(self):
        self.path = server.ROOT / 'app' / 'test_data' / ('learning-' + uuid.uuid4().hex + '.db')
        self.addCleanup(self.remove_database)
        modules = [server] + [getattr(server, f'ege{n}_module') for n in (5,10,11,12,13,14,15)]
        for module in modules:
            p = patch.object(module, 'DB_PATH', self.path)
            p.start(); self.addCleanup(p.stop)
        with patch.object(server, 'PASSWORD_HASH_ITERATIONS', 1), patch.object(server, 'seed_demo_users', return_value=True):
            server.ensure_app_db()
        with server.db() as con:
            self.teacher = dict(con.execute("SELECT * FROM users WHERE username='teacher'").fetchone())
            self.student = dict(con.execute("SELECT * FROM users WHERE username='student'").fetchone())
            server.insert_user_consent(con, self.teacher['user_id'], '', '')
            server.insert_user_consent(con, self.student['user_id'], '', '')

    def remove_database(self):
        gc.collect()
        self.path.unlink(missing_ok=True)

    def create(self, config=None, **kwargs):
        return learning.create_test(server, self.teacher, {'title':'Проверка', 'student_ids':[self.student['user_id']],
            'config':config or {'activity':'ege9','mode':'line','count':2}, **kwargs})

    def test_ege9_mixed_rows_and_answer_key(self):
        for _ in range(200):
            q = server.make_line_question()
            ids = [i for row in q['row_word_ids'] for i in row]
            self.assertEqual(len(set(ids)), 15)
            categories = {server.WORD_BY_ID[i]['category'] for i in ids}
            self.assertGreaterEqual(len(categories), 3)
            correct = ''.join(str(index+1) for index, row in enumerate(q['row_word_ids'])
                if len({server.WORD_BY_ID[i]['correct_letter'] for i in row}) == 1)
            self.assertEqual(correct, q['_correct_answer'])
            self.assertIn(len(correct), (2,3))

    def test_groups_ownership_and_notifications(self):
        group = learning.save_group(server, self.teacher, {'title':'Группа А','student_ids':[self.student['user_id']]})
        test = self.create(student_ids=[], group_ids=[group['id']])
        self.assertEqual(test['recipients'],1)
        data = learning.overview(server,self.student)
        self.assertEqual(data['unread'],1)
        learning.open_test(server,self.student,{'test_id':test['id']})
        self.assertEqual(learning.overview(server,self.student)['unread'],0)
        other = {**self.student,'user_id':'another_student'}
        with self.assertRaises(PermissionError): learning.open_test(server,other,{'test_id':test['id']})
        with self.assertRaises(PermissionError): self.create(student_ids=['another_student'])
        with self.assertRaises(PermissionError): learning.create_test(server,self.student,{})

    def test_frozen_variant_resume_statistics_and_idempotency(self):
        test = self.create()
        payload = {'test_id':test['id']}
        opened = learning.open_test(server,self.student,payload)
        self.assertEqual(opened['questions'],learning.open_test(server,self.student,payload)['questions'])
        self.assertNotIn('correct_answer',json.dumps(opened['questions']))
        with server.db() as con:
            snapshots = json.loads(con.execute('SELECT questions_json FROM assigned_tests WHERE id=?',(test['id'],)).fetchone()[0])
        answers = {s['question_id']:s['question']['correct_answer'] for s in snapshots}
        learning.save_answers(server,self.student,{**payload,'answers':answers})
        server.PRACTICE_SESSIONS.clear()
        self.assertEqual(learning.open_test(server,self.student,payload)['answers'],answers)
        result = learning.save_answers(server,self.student,{**payload,'answers':answers},submit=True)
        self.assertEqual((result['correct'],result['total']),(2,2))
        attempts_before = server.progress_for(self.student)['summary']['total']
        again = learning.save_answers(server,self.student,{**payload,'answers':{}},submit=True)
        self.assertEqual(result,again)
        self.assertEqual(server.progress_for(self.student)['summary']['total'],attempts_before)
        self.assertEqual(learning.overview(server,self.teacher)['tests'][0]['students'][0]['result']['correct'],2)

    def test_mixed_test_all_modules_use_personal_error_banks(self):
        test = self.create({'activity':'orthography-ege','task_counts':{f'ege{n}':1 for n in range(9,16)}})
        opened = learning.open_test(server,self.student,{'test_id':test['id']})
        self.assertEqual(len(opened['questions']),7)
        public = json.dumps(opened['questions'])
        for field in ('correct_answer','word_answers','sentence_items','exam_rows','line_items'):
            self.assertNotIn('"'+field+'":',public)
        result = learning.save_answers(server,self.student,{'test_id':test['id'],'answers':{}},submit=True)
        self.assertEqual(result['total'],7)
        with server.db() as con:
            self.assertGreater(con.execute('SELECT COUNT(*) FROM word_progress WHERE user_id=? AND due_reviews>0',(self.student['user_id'],)).fetchone()[0],0)
        # The paronym module has its own answer normalizer.
        t = self.create({'activity':'ege5','mode':'paronym_exam','count':1})
        self.assertEqual(learning.save_answers(server,self.student,{'test_id':t['id'],'answers':{}},submit=True)['total'],1)

    def test_game_answers_in_student_and_teacher_statistics(self):
        payload = {'slug':'autumn-leaves','event_id':'unique-event','is_correct':False,'prompt':'слово','given_answer':'и','correct_answer':'ы'}
        self.assertTrue(learning.game_result(server,self.student,payload)['recorded'])
        self.assertFalse(learning.game_result(server,self.student,payload)['recorded'])
        for user in (self.student,self.teacher):
            data = server.progress_for(user)
            self.assertEqual(data['by_game'][0]['total'],1)
            self.assertEqual(data['by_game'][0]['correct'],0)
            self.assertEqual(data['incorrect_attempts'][0]['prompt'],'слово')
        with self.assertRaises(ValueError): learning.game_result(server,self.student,{**payload,'slug':'unknown'})

    def test_teacher_can_assign_class_error_words(self):
        word = server.WORDS[0]
        with server.db() as con:
            server.update_error_bank_progress(con,self.student['user_id'],word['id'],False)
        test = self.create({'activity':'ege9','mode':'errors','count':5})
        opened = learning.open_test(server,self.student,{'test_id':test['id']})
        self.assertEqual(len(opened['questions']),1)
        self.assertEqual(opened['questions'][0]['source_word_id'],word['id'])
        self.assertNotIn('correct_answer',opened['questions'][0])
        result = learning.save_answers(server,self.student,{'test_id':test['id'],'answers':{}},submit=True)
        self.assertEqual(result['total'],1)

    @unittest.skipUnless(shutil.which('node'), 'Node.js is required for game script checks')
    def test_every_online_game_has_valid_answer_hooks(self):
        seen = set()
        for slug, folder in {**server.HTML_GAMES,**server.PUBLIC_GAMES}.items():
            if folder in seen:
                continue
            seen.add(folder)
            hooks = 0
            for path in [folder/server.game_entry_file(slug,'index.html')] + list(folder.glob('*.js')):
                if not path.exists():
                    continue
                html = path.suffix == '.html'
                source = game_tracking.transform(slug,path.read_bytes(),html=html).decode('utf-8')
                hooks += source.count('recordLearningGameAnswer?.')
                scripts = [m[1] for m in re.finditer(r'<script\b[^>]*>(.*?)</script>',source,re.S|re.I)
                    if m[1].strip() and not re.match(r'\s*(?:\{|\[)',m[1])] if html else [source]
                for script in scripts:
                    checked = subprocess.run(['node','--check'],input=script.encode('utf-8'),capture_output=True)
                    self.assertEqual(checked.returncode,0,f'{slug}/{path.name}: {checked.stderr.decode(errors="replace")}')
            self.assertGreater(hooks,0,slug)

    def test_http_auth_and_online_hooks(self):
        http = ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        thread = threading.Thread(target=http.serve_forever,daemon=True);thread.start()
        self.addCleanup(http.server_close);self.addCleanup(http.shutdown)
        base = f'http://127.0.0.1:{http.server_port}'
        with self.assertRaises(HTTPError) as error: urlopen(base+'/api/assignments')
        self.assertEqual(error.exception.code,401)
        server.SESSIONS['learning-test']={'user':self.student}
        self.addCleanup(lambda:server.SESSIONS.pop('learning-test',None))
        response = urlopen(Request(base+'/api/assignments',headers={'Authorization':'Bearer learning-test'}))
        self.assertEqual(json.load(response)['pending'],0)
        for route in ('/games/autumn-leaves/index.html','/html-games/autumn-leaves/index.html','/Full-79328410563827-autumn-leaves/index.html'):
            with patch.object(server,'record_public_game_visit'):
                html = urlopen(base+route).read().decode('utf-8')
            self.assertIn('game-tracker.js',html)
            self.assertIn('recordLearningGameAnswer?.(correct,q.variant,letter,q.answer)',html)


if __name__ == '__main__':
    unittest.main()
