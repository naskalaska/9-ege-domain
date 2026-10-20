import json
import random
import sqlite3
import unittest

import learning_module as learning
import server
import statistics_module as statistics
import test_learning as fixtures


class AssignmentManagementTest(unittest.TestCase):
    def setUp(self):
        self.case = fixtures.LearningTest()
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.teacher, self.student = self.case.teacher, self.case.student

    def payload(self, test):
        return {'test_id':test['id'],'student_id':self.student['user_id']}

    def test_frozen_assigned_rows_keys_and_explanations_follow_shuffle(self):
        state = random.getstate()
        self.addCleanup(random.setstate,state)
        random.seed(20261020)
        for task in (9,10,11,12):
            module = server if task == 9 else getattr(server,f'ege{task}_module')
            test = self.case.create({'activity':f'ege{task}','mode':'line','count':30})
            keys = set()
            for snap in self.case.snapshots(test['id']):
                question = snap['question']
                rows = question.get('row_word_ids') or [r['word_ids'] for r in question['line_rows']]
                key = ''.join(str(i) for i,ids in enumerate(rows,1)
                              if len({module.WORD_BY_ID[wid]['correct_letter'] for wid in ids})==1)
                self.assertEqual(key,question['correct_answer'])
                self.assertIn('Правильные строки: '+', '.join(key),question['explanation'])
                self.assertNotIn('correct_answer',snap['public'])
                self.assertNotIn('explanation',snap['public'])
                keys.add(key)
            self.assertGreater(len(keys),8,(task,keys))

    def test_teacher_results_are_scoped_to_test_student_and_keep_partial_answers(self):
        test = self.case.create({'activity':'ege11','mode':'line','count':3})
        first,second,third = self.case.snapshots(test['id'])
        learning.check_question(server,self.student,{'test_id':test['id'],
            'question_id':first['question_id'],'answer':first['question']['correct_answer']})
        learning.save_answers(server,self.student,{'test_id':test['id'],
            'answers':{second['question_id']:'15'}})
        results = learning.test_results(server,self.teacher,self.payload(test))
        self.assertEqual((results['total'],results['checked'],results['correct']),(3,1,1))
        self.assertEqual([r['status'] for r in results['items']],['checked','draft','unanswered'])
        for row,snap in zip(results['items'],(first,second,third)):
            self.assertEqual(row['correct_answer'],snap['question']['correct_answer'])
            self.assertIn('5)',row['prompt'])
            self.assertIn('1)',row['prompt'])
        self.assertEqual(results['items'][1]['given_answer'],'15')
        self.assertIsNone(results['items'][1]['is_correct'])
        other = self.case.create({'activity':'ege9','mode':'line','count':1})
        self.assertEqual(learning.test_results(server,self.teacher,self.payload(other))['checked'],0)
        for user in (self.student,{**self.teacher,'user_id':'other-teacher'}):
            for action in (learning.test_results,learning.revoke_test):
                with self.assertRaises(PermissionError): action(server,user,self.payload(test))
        for action in (learning.test_results,learning.revoke_test):
            with self.assertRaises(PermissionError):
                action(server,self.teacher,{'test_id':test['id'],'student_id':'other-student'})

    def test_revoke_blocks_open_save_check_and_submit_preserving_history(self):
        test = self.case.create({'activity':'ege9','mode':'line','count':2})
        snap = self.case.snapshots(test['id'])[0]
        learning.open_test(server,self.student,self.payload(test))
        learning.check_question(server,self.student,{**self.payload(test),
            'question_id':snap['question_id'],'answer':snap['question']['correct_answer']})
        with server.db() as con:
            count = con.execute('SELECT COUNT(*) FROM attempts').fetchone()[0]
        learning.revoke_test(server,self.teacher,self.payload(test))
        learning.revoke_test(server,self.teacher,self.payload(test))
        with self.assertRaises(PermissionError): learning.open_test(server,self.student,self.payload(test))
        with self.assertRaises(PermissionError): learning.save_answers(server,self.student,{**self.payload(test),'answers':{}})
        with self.assertRaises(PermissionError): learning.save_answers(server,self.student,{**self.payload(test),'answers':{}},submit=True)
        with self.assertRaises(PermissionError): learning.check_question(server,self.student,self.payload(test))
        student = learning.overview(server,self.student)
        self.assertEqual((student['pending'],student['unread']),(0,0))
        self.assertTrue(student['tests'][0]['revoked_at'])
        results = learning.test_results(server,self.teacher,self.payload(test))
        self.assertEqual((results['checked'],results['correct']),(1,1))
        with server.db() as con:
            self.assertEqual(con.execute('SELECT COUNT(*) FROM attempts').fetchone()[0],count)

    def test_revoke_single_recipient_then_everyone_and_completed_results_remain(self):
        with server.db() as con:
            con.execute('''INSERT INTO users(user_id,username,display_name,role,password_salt,password_hash,created_at,teacher_id)
                VALUES('second-pupil','second-pupil','Второй ученик','student','','','2026-10-20',?)''',
                (self.teacher['user_id'],))
            second = dict(con.execute("SELECT * FROM users WHERE user_id='second-pupil'").fetchone())
        test = self.case.create({'activity':'ege11','mode':'line','count':1},
                                student_ids=[self.student['user_id'],second['user_id']])
        snap = self.case.snapshots(test['id'])[0]
        learning.check_question(server,self.student,{**self.payload(test),
            'question_id':snap['question_id'],'answer':snap['question']['correct_answer']})
        learning.revoke_test(server,self.teacher,self.payload(test))
        self.assertEqual(learning.open_test(server,self.student,self.payload(test))['result']['correct'],1)
        self.assertIsNone(learning.overview(server,second)['tests'][0]['revoked_at'])
        learning.revoke_test(server,self.teacher,{'test_id':test['id']})
        self.assertTrue(learning.overview(server,second)['tests'][0]['revoked_at'])
        self.assertEqual(learning.test_results(server,self.teacher,self.payload(test))['correct'],1)

    def test_word_diagnostic_with_same_question_id_never_inherits_test_rows_or_explanation(self):
        test = self.case.create({'activity':'ege11','mode':'line','count':1})
        snap = self.case.snapshots(test['id'])[0]
        # Choosing every row guarantees an error and creates word diagnostics.
        learning.check_question(server,self.student,{**self.payload(test),
            'question_id':snap['question_id'],'answer':'12345'})
        rows = statistics.history(server,self.student,{'kind':'all','page_size':100})['items']
        main = next(row for row in rows if not row['is_detail'])
        self.assertEqual(main['correct_answer'],snap['question']['correct_answer'])
        self.assertIn('5)',main['prompt'])
        details = [row for row in rows if row['is_detail']]
        self.assertTrue(details)
        for row in details:
            self.assertNotIn('5)',row['prompt'])
            self.assertNotIn('Правильные строки:',row['explanation'])
            self.assertEqual(row['detail_kind'],'row_selection')

    def test_legacy_completed_results_without_per_question_checks(self):
        test = self.case.create({'activity':'ege9','mode':'line','count':1})
        snap = self.case.snapshots(test['id'])[0]
        result = learning.save_answers(server,self.student,{**self.payload(test),
            'answers':{snap['question_id']:snap['question']['correct_answer']}},submit=True)
        with server.db() as con:
            con.execute('DELETE FROM assigned_test_checks WHERE test_id=?',(test['id'],))
        actual = learning.test_results(server,self.teacher,self.payload(test))
        self.assertEqual((actual['checked'],actual['correct']),(1,result['correct']))
        self.assertEqual(actual['items'][0]['status'],'checked')

    def test_schema_upgrade_is_idempotent_and_preserves_old_assignments(self):
        with sqlite3.connect(':memory:') as con:
            con.execute('''CREATE TABLE assigned_test_students(test_id TEXT,student_id TEXT,seen_at TEXT,
                started_at TEXT,completed_at TEXT,answers_json TEXT,result_json TEXT,PRIMARY KEY(test_id,student_id))''')
            con.execute("INSERT INTO assigned_test_students(test_id,student_id,answers_json) VALUES('old','student','{}')")
            learning.ensure_schema(con)
            learning.ensure_schema(con)
            row = con.execute('SELECT answers_json,revoked_at FROM assigned_test_students').fetchone()
            self.assertEqual(row,('{}',None))


if __name__ == '__main__':
    unittest.main()
