import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from unittest.mock import patch
import test_learning as fixtures
import server
import learning_module as learning
import game_assignments as games
import student_workspace as workspace
import statistics_module as statistics


class GameAssignmentsTest(unittest.TestCase):
    def setUp(self):
        self.case=fixtures.LearningTest();self.case.setUp();self.addCleanup(self.case.doCleanups)
        self.teacher,self.student=self.case.teacher,self.case.student

    def buy(self,slug='autumn-herbarium',status='paid'):
        with server.db() as con:
            pid=con.execute('SELECT product_id FROM paid_entities WHERE slug=?',(slug,)).fetchone()[0]
            con.execute('''INSERT INTO shop_orders(order_uid,product_id,buyer_email,status,created_at)
                VALUES(?,?,?,?,?)''',('order-'+slug,pid,server.normalize_email(self.teacher.get('email') or self.teacher['username']),status,server.now_iso()))
        return pid

    def assign(self,**extra):
        return games.create(server,self.teacher,{'slug':'autumn-herbarium','student_ids':[self.student['user_id']],**extra})

    def answer(self,assignment,event='one',**extra):
        return learning.game_result(server,self.student,{'slug':'autumn-herbarium','assignment_id':assignment['id'],
            'event_id':event,'is_correct':False,'prompt':'ц..плёнок','given_answer':'и','correct_answer':'ы',**extra})

    def test_only_owned_games_and_own_students_can_be_assigned(self):
        with self.assertRaises(PermissionError):self.assign()
        self.buy(status='pending')
        with self.assertRaises(PermissionError):self.assign()
        with server.db() as con:con.execute("UPDATE shop_orders SET status='paid'")
        self.assertTrue(next(g for g in server.teacher_games(self.teacher)['purchased'] if g['slug']=='autumn-herbarium')['can_assign'])
        with self.assertRaises(PermissionError):self.assign(student_ids=['someone-else'])
        with self.assertRaises(PermissionError):games.create(server,self.student,{'slug':'autumn-herbarium','student_ids':[self.student['user_id']]})
        with self.assertRaises(ValueError):self.assign(target_count=501)
        group=learning.save_group(server,self.teacher,{'title':'Группа','student_ids':[self.student['user_id']]})
        assigned=self.assign(group_ids=[group['id']],all_students=True)
        self.assertEqual(assigned['recipients'],1)
        self.assertEqual(learning.overview(server,self.student)['pending'],1)
        self.assertEqual(learning.overview(server,self.student)['unread'],1)

    def test_full_game_access_ownership_revocation_and_refund(self):
        self.buy();assignment=self.assign()
        url=games.open_game(server,self.student,{'game_id':assignment['id']})['url']
        self.assertTrue(url.startswith('/assigned-games/'))
        self.assertNotIn('Full-',url)
        with server.db() as con:
            with self.assertRaises(PermissionError):games.check_access(server,con,{**self.student,'user_id':'other'},assignment['id'])
            self.assertEqual(games.check_access(server,con,self.student,assignment['id'])['kind'],'full')
            con.execute("UPDATE shop_orders SET status='refunded'")
        with self.assertRaises(PermissionError):games.open_game(server,self.student,{'game_id':assignment['id']})
        with server.db() as con:con.execute("UPDATE shop_orders SET status='paid'")
        games.update(server,self.teacher,{'game_id':assignment['id'],'student_id':self.student['user_id'],'revoke':True})
        with self.assertRaises(PermissionError):games.open_game(server,self.student,{'game_id':assignment['id']})
        with self.assertRaises(PermissionError):self.answer(assignment)

    def test_progress_is_idempotent_in_personal_statistics_profile_calendar(self):
        self.buy();assignment=self.assign(target_count=2,due_at='2020-01-01T00:00:00Z')
        self.assertTrue(games.overview(server,self.student)[0]['overdue'])
        self.assertTrue(self.answer(assignment)['recorded'])
        self.assertFalse(self.answer(assignment)['recorded'])
        self.answer(assignment,'two',is_correct=True)
        progress=games.overview(server,self.teacher)[0]
        self.assertEqual((progress['checked'],progress['correct']),(2,1))
        self.assertTrue(progress['completed_at']);self.assertTrue(progress['submitted_late'])
        self.assertTrue(games.open_game(server,self.student,{'game_id':assignment['id']}))
        self.assertEqual(statistics.overview(server,self.student)['summary']['total'],2)
        self.assertEqual(workspace.profile(server,self.student,{})['assignments'][0]['assignment_kind'],'game')
        self.assertEqual(workspace.calendar(server,self.student,{})['items'][0]['id'],assignment['id'])
        self.assertEqual(learning.overview(server,self.student)['pending'],0)
        with self.assertRaises(PermissionError):self.answer(assignment,'wrong-game',slug='autumn-leaves')
        with self.assertRaises(PermissionError):games.update(server,self.student,{'game_id':assignment['id'],'due_at':None})
        games.update(server,self.teacher,{'game_id':assignment['id'],'due_at':None})
        self.assertIsNone(games.overview(server,self.student)[0]['due_at'])

    def test_gift_and_created_game_and_disabled_set(self):
        with server.db() as con:
            pid=con.execute("SELECT product_id FROM paid_entities WHERE slug='autumn-herbarium'").fetchone()[0]
            con.execute('INSERT INTO teacher_product_gifts VALUES(?,?,?,?,?)',
                (self.teacher['user_id'],pid,'подарок',self.teacher['user_id'],server.now_iso()))
        self.assertTrue(self.assign())
        with server.db() as con:
            created=server.save_game_set(con,self.teacher,{'title':'Мой набор','mechanic':'autumn-leaves','items':[]},'upload')
        assignment=self.assign(public_id=created['public_id'])
        self.assertIn('set='+created['public_id'],games.open_game(server,self.student,{'game_id':assignment['id']})['url'])
        with server.db() as con:con.execute('UPDATE game_sets SET is_active=0 WHERE public_id=?',(created['public_id'],))
        with self.assertRaises(PermissionError):games.open_game(server,self.student,{'game_id':assignment['id']})
        with self.assertRaises(PermissionError):self.assign(public_id=created['public_id'])

    def test_transfer_current_membership_checked_even_with_stale_session(self):
        self.buy();assignment=self.assign()
        with server.db() as con:con.execute('UPDATE users SET teacher_id=NULL WHERE user_id=?',(self.student['user_id'],))
        with self.assertRaises(PermissionError):games.open_game(server,self.student,{'game_id':assignment['id']})

    def test_full_http_page_and_assets_are_not_demo_or_public(self):
        self.buy();assignment=self.assign()
        http=ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        threading.Thread(target=http.serve_forever,daemon=True).start()
        self.addCleanup(http.server_close);self.addCleanup(http.shutdown)
        server.SESSIONS['assigned-game-test']={'user':self.student}
        self.addCleanup(lambda:server.SESSIONS.pop('assigned-game-test',None))
        base=f'http://127.0.0.1:{http.server_port}'
        url=games.open_game(server,self.student,{'game_id':assignment['id']})['url']
        with self.assertRaises(HTTPError):urlopen(base+url)
        request=lambda path:Request(base+path,headers={'Authorization':'Bearer assigned-game-test'})
        with patch.object(server,'record_public_game_visit'):
            response=urlopen(request(url));html=response.read().decode('utf-8')
        self.assertIn('no-store',response.headers['Cache-Control'])
        self.assertIn('fileInput',html);self.assertIn('value="all"',html)
        self.assertNotIn('site-demo-ribbon',html)
        self.assertIn('game-tracker.js?v=20261020-assigned-games',html)
        games.update(server,self.teacher,{'game_id':assignment['id'],'revoke':True})
        with self.assertRaises(HTTPError):urlopen(request(url))

    def test_account_cleanup_keeps_statistics_while_revoked_and_deletes_grants(self):
        self.buy();assignment=self.assign();self.answer(assignment)
        games.update(server,self.teacher,{'game_id':assignment['id'],'revoke':True})
        self.assertEqual(statistics.overview(server,self.student)['summary']['total'],1)
        with server.db() as con:
            server.delete_user_records(con,self.student['user_id'])
            self.assertEqual(con.execute('SELECT COUNT(*) FROM assigned_game_students').fetchone()[0],0)
            self.assertEqual(con.execute('SELECT COUNT(*) FROM assigned_game_answers').fetchone()[0],0)


if __name__=='__main__':unittest.main()
