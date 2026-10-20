import json
import sqlite3
import unittest
from datetime import datetime, timezone
import learning_module as learning
import statistics_module as statistics
import student_workspace as workspace
import test_learning as fixtures
import server


class StudentWorkspaceTest(unittest.TestCase):
    def setUp(self):
        self.case=fixtures.LearningTest();self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.teacher,self.student=self.case.teacher,self.case.student

    def check(self,test,snap,answer):
        return learning.check_question(server,self.student,{'test_id':test['id'],'question_id':snap['question_id'],'answer':answer})

    def make_error(self,activity='ege9'):
        mode={'ege13':'line_ne','ege14':'exam','ege15':'sentence_nn','ege5':'paronym_exam'}.get(activity,'line')
        test=self.case.create({'activity':activity,'mode':mode,'count':1})
        snap=self.case.snapshots(test['id'])[0]
        wrong={'ege5':{'row':'1','word':'ошибка'},'ege15':{i:'ошибка' for i in snap['question'].get('sentence_items',[])}}.get(activity,'12345')
        self.check(test,snap,wrong)
        item=statistics.history(server,self.student,{'kind':'answers','activity':activity})['items'][0]
        self.assertFalse(item['is_correct'])
        return test,snap,item

    def test_deadlines_remain_solvable_after_overdue_and_late_completion(self):
        test=self.case.create({'activity':'ege9','mode':'line','count':1},due_at='2020-01-01T14:00:00+03:00')
        item=learning.overview(server,self.student)['tests'][0]
        self.assertEqual(item['due_at'],'2020-01-01T11:00:00+00:00')
        self.assertTrue(item['overdue'])
        opened=learning.open_test(server,self.student,{'test_id':test['id']})
        snap=self.case.snapshots(test['id'])[0]
        self.assertTrue(self.check(test,snap,snap['question']['correct_answer'])['result'])
        item=learning.overview(server,self.student)['tests'][0]
        self.assertFalse(item['overdue']);self.assertTrue(item['submitted_late'])
        self.assertTrue(learning.open_test(server,self.student,{'test_id':test['id']})['result'])
        self.assertEqual(workspace.calendar(server,self.student,{})['items'][0]['due_at'],item['due_at'])

    def test_edit_clear_deadline_and_permissions(self):
        test=self.case.create()
        params={'test_id':test['id'],'student_id':self.student['user_id'],'due_at':'2050-01-01T00:00:00Z'}
        learning.set_deadline(server,self.teacher,params)
        self.assertFalse(learning.overview(server,self.student)['tests'][0]['overdue'])
        with self.assertRaises(PermissionError):learning.set_deadline(server,self.student,params)
        with self.assertRaises(PermissionError):learning.set_deadline(server,{**self.teacher,'user_id':'other'},params)
        with self.assertRaises(PermissionError):learning.set_deadline(server,self.teacher,{**params,'student_id':'other'})
        for due in ('tomorrow','2026-10-20T12:00:00','2026-50-01'):
            with self.assertRaises(ValueError):learning.set_deadline(server,self.teacher,{**params,'due_at':due})
        learning.set_deadline(server,self.teacher,{**params,'due_at':None})
        self.assertIsNone(learning.overview(server,self.student)['tests'][0]['due_at'])

    def test_profile_groups_statistics_trend_and_ownership(self):
        self.make_error()
        learning.save_group(server,self.teacher,{'title':'Группа А','student_ids':[self.student['user_id']]})
        profile=workspace.profile(server,self.teacher,{'student_id':self.student['user_id'],'offset_minutes':180})
        self.assertEqual(profile['student']['display_name'],self.student['display_name'])
        self.assertEqual(profile['groups'][0]['title'],'Группа А')
        self.assertEqual(profile['statistics']['summary']['total'],1)
        self.assertEqual(len(profile['trend']),8)
        self.assertEqual(sum(w['total'] for w in profile['trend']),1)
        self.assertEqual(len(profile['assignments']),1)
        self.assertEqual(workspace.profile(server,self.student,{})['statistics']['summary']['total'],1)
        for action in (workspace.profile,workspace.calendar):
            with self.assertRaises(PermissionError):action(server,self.student,{'student_id':'other'})
            with self.assertRaises(PermissionError):action(server,self.teacher,{'student_id':'other'})

    def test_repeat_frozen_exam_all_tasks_exact_key_new_id_and_private_key(self):
        for activity in ('ege5','ege9','ege10','ege11','ege12','ege13','ege14','ege15'):
            with self.subTest(activity=activity):
                test,snap,item=self.make_error(activity)
                repeated=workspace.repeat_error(server,self.student,{'attempt_id':item['attempt_id']})
                frozen=self.case.snapshots(repeated['id'])[0]
                self.assertEqual(frozen['question']['correct_answer'],snap['question']['correct_answer'])
                self.assertNotEqual(frozen['question_id'],snap['question_id'])
                self.assertEqual(frozen['public']['rows'] if 'rows' in frozen['public'] else frozen['public']['parts'],
                                 snap['public']['rows'] if 'rows' in snap['public'] else snap['public']['parts'])
                public=learning.open_test(server,self.student,{'test_id':repeated['id']})['questions'][0]
                self.assertNotIn('correct_answer',public)
                self.assertNotIn('correct_spelling',public)
                self.assertEqual(workspace.repeat_error(server,self.student,{'attempt_id':item['attempt_id']})['id'],repeated['id'])
                answer=frozen['question']['correct_answer']
                if activity=='ege5':
                    row,word=answer.split('|',1);answer={'row':row,'word':word}
                result=self.check(repeated,frozen,answer)
                self.assertTrue(result['checked_result']['is_correct'])
                with server.db() as con:
                    self.assertEqual(con.execute('SELECT is_correct FROM attempts WHERE attempt_id=?',(item['attempt_id'],)).fetchone()[0],0)

    def test_teacher_assigns_word_repeat_with_deadline_and_unauthorized_cannot(self):
        test,snap,item=self.make_error('ege11')
        detail=statistics.history(server,self.student,{'activity':'ege11','kind':'details'})['items'][0]
        payload={'attempt_id':detail['attempt_id'],'due_at':'2020-01-01T00:00:00Z'}
        with self.assertRaises(PermissionError):workspace.repeat_error(server,{**self.teacher,'user_id':'other'},payload)
        with self.assertRaises(PermissionError):workspace.repeat_error(server,self.student,payload)
        result=workspace.repeat_error(server,self.teacher,payload)
        snap=self.case.snapshots(result['id'])[0]
        self.assertEqual(snap['question']['source_word_id'],detail['word_id'])
        self.assertNotEqual(snap['question']['kind'],'line')
        self.assertTrue(next(t for t in learning.overview(server,self.student)['tests'] if t['id']==result['id'])['overdue'])

    def test_legacy_full_rows_replayed_but_lost_content_is_not_invented(self):
        with server.db() as con:
            con.execute('''INSERT INTO attempts(attempt_id,user_id,mode,scope_id,question_id,prompt,
                given_answer,correct_answer,is_correct,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)''',
                ('old',self.student['user_id'],'line','ege9:line','q','Выберите строки\n1) раз\n2) два\n3) три\n4) четыре\n5) пять','12','35',0,server.now_iso()))
        result=workspace.repeat_error(server,self.student,{'attempt_id':'old'})
        snap=self.case.snapshots(result['id'])[0]
        self.assertEqual(snap['question']['kind'],'error_review')
        self.assertTrue(self.check(result,snap,'53')['checked_result']['is_correct'])
        with server.db() as con:con.execute("UPDATE attempts SET prompt='Только инструкция' WHERE attempt_id='old'")
        with self.assertRaises(ValueError):workspace.repeat_error(server,self.student,{'attempt_id':'old'})

    def test_schema_upgrades_preserve_old_rows(self):
        with sqlite3.connect(':memory:') as con:
            con.execute('''CREATE TABLE assigned_test_students(test_id TEXT,student_id TEXT,seen_at TEXT,
                started_at TEXT,completed_at TEXT,answers_json TEXT,result_json TEXT,PRIMARY KEY(test_id,student_id))''')
            con.execute("INSERT INTO assigned_test_students(test_id,student_id,answers_json) VALUES('old','student','{}')")
            learning.ensure_schema(con);learning.ensure_schema(con)
            self.assertEqual(con.execute('SELECT answers_json,due_at FROM assigned_test_students').fetchone(),('{}',None))

    def test_repeat_from_normal_result_question_id_and_game_letter(self):
        module=server.ege11_module
        data=module.start_practice(self.student,{'mode':'mix','count':1})
        question=next(iter(module.PRACTICE_SESSIONS[data['session_id']]['questions'].values()))
        with server.db() as con:
            module.record_attempt(con,self.student['user_id'],module.PRACTICE_SESSIONS[data['session_id']],
                question['question_id'],question,'ошибка')
        result=workspace.repeat_error(server,self.student,{'question_id':question['question_id']})
        snap=self.case.snapshots(result['id'])[0]
        self.assertEqual(snap['question']['source_word_id'],question['source_word_id'])
        self.assertTrue(self.check(result,snap,snap['question']['correct_answer'])['checked_result']['is_correct'])
        learning.game_result(server,self.student,{'slug':'autumn-leaves','event_id':'letter-error',
            'is_correct':False,'prompt':'ц..плёнок','given_answer':'и','correct_answer':'ы'})
        item=statistics.history(server,self.student,{'activity':'games'})['items'][0]
        self.assertTrue(item['can_repeat'])
        result=workspace.repeat_error(server,self.student,{'attempt_id':item['attempt_id']})
        snap=self.case.snapshots(result['id'])[0]
        self.assertEqual(snap['question']['kind'],'error_review')
        self.assertTrue(self.check(result,snap,'ы')['checked_result']['is_correct'])
        self.assertEqual(statistics.overview(server,self.student)['summary']['total'],4)

    def test_account_deletion_cleans_repeat_links_and_checks(self):
        test,snap,item=self.make_error()
        repeated=workspace.repeat_error(server,self.student,{'attempt_id':item['attempt_id']})
        snap=self.case.snapshots(repeated['id'])[0]
        self.check(repeated,snap,snap['question']['correct_answer'])
        with server.db() as con:
            self.assertGreater(con.execute('SELECT COUNT(*) FROM error_repetitions').fetchone()[0],0)
            server.delete_user_records(con,self.student['user_id'])
            self.assertEqual(con.execute('SELECT COUNT(*) FROM error_repetitions').fetchone()[0],0)
            self.assertEqual(con.execute('SELECT COUNT(*) FROM assigned_test_checks').fetchone()[0],0)


if __name__=='__main__':unittest.main()
