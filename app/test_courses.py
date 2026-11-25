import gc
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from datetime import datetime, timezone, timedelta
import server
import courses


class CoursesTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=server.ROOT/'tmp')
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(gc.collect)
        self.dbpath=Path(self.temp.name)/'test.db'
        p=patch.object(server,'DB_PATH',self.dbpath);p.start();self.addCleanup(p.stop)
        with patch.object(server,'PASSWORD_HASH_ITERATIONS',1),patch.object(server,'seed_demo_users',return_value=True):
            server.ensure_app_db()
        with server.db() as con:
            self.admin=dict(con.execute("SELECT * FROM users WHERE role='admin' LIMIT 1").fetchone())
            self.student=dict(con.execute("SELECT * FROM users WHERE username='student'").fetchone())
            self.teacher=dict(con.execute("SELECT * FROM users WHERE username='teacher'").fetchone())

    def purchase(self,user=None):
        user=user or self.student
        with server.db() as con:
            con.execute("INSERT INTO shop_orders(order_uid,product_id,product_title,amount,currency,buyer_email,status,created_at) VALUES (?,?,?,'5000.00','RUB',?,'paid',?)",('order-'+user['user_id'],courses.PRODUCT,courses.TITLE,user.get('email') or user['username'],server.now_iso()))

    def test_seed_and_access(self):
        with server.db() as con:
            self.assertEqual(con.execute('SELECT amount FROM paid_entities WHERE product_id=?',(courses.PRODUCT,)).fetchone()[0],'5000.00')
            self.assertEqual(con.execute("SELECT amount FROM paid_entities WHERE product_id='personal-consultation'").fetchone()[0],'2000.00')
        with self.assertRaises(PermissionError): courses.overview(server,self.student)
        self.purchase()
        data=courses.overview(server,self.student)
        self.assertTrue(data['lessons'][0]['available'])
        self.assertFalse(any(x['available'] for x in data['lessons'][1:]))
        self.assertIn('max.ru/join',data['settings']['chat'])
        with self.assertRaises(PermissionError): courses.content(server,self.student,'2')
        with self.assertRaises(PermissionError): courses.action(server,self.student,{'action':'progress','lesson_id':2,'data':{}})
        with self.assertRaises(PermissionError): courses.overview(server,self.student,True)

    def test_source_homework_preserves_admin_edits(self):
        data=courses.overview(server,self.admin,True)
        self.assertIn('Короткий запрос',data['lessons'][1]['homework'])
        custom='Моё обновлённое задание для второго урока'
        courses.action(server,self.admin,{'action':'lesson','id':2,'data':{'homework':custom}})
        with server.db() as con:
            courses.seed(con,server)
        self.assertEqual(courses.overview(server,self.admin,True)['lessons'][1]['homework'],custom)

    def test_groups_and_global_schedule(self):
        self.purchase()
        courses.overview(server,self.student)
        courses.action(server,self.admin,{'action':'group','id':'g','title':'Группа 1','schedule':{'2':'','3':(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()}})
        courses.action(server,self.admin,{'action':'member','user_id':self.student['user_id'],'group_id':'g'})
        data=courses.overview(server,self.student)
        self.assertTrue(data['lessons'][1]['available'])
        self.assertFalse(data['lessons'][2]['available'])
        self.assertIn('homework',data['lessons'][1])
        self.assertNotIn('homework',data['lessons'][2])
        courses.action(server,self.admin,{'action':'lesson','id':4,'data':{'opens_at':''}})
        self.assertTrue(courses.overview(server,self.student)['lessons'][3]['available'])

    def test_answers_private_and_replies(self):
        self.purchase();self.purchase(self.teacher)
        courses.action(server,self.student,{'action':'progress','lesson_id':1,'data':{'fields':{'answer':'Мой ответ'},'completed':True}})
        courses.action(server,self.student,{'action':'message','lesson_id':1,'kind':'homework','body':'https://example.com/result'})
        self.assertFalse(courses.overview(server,self.teacher)['messages'])
        admin=courses.overview(server,self.admin,True)
        self.assertEqual(admin['progress'][0]['data']['fields']['answer'],'Мой ответ')
        mid=admin['messages'][0]['id']
        with self.assertRaises(PermissionError): courses.action(server,self.student,{'action':'reply','id':mid,'reply':'bad'})
        courses.action(server,self.admin,{'action':'reply','id':mid,'reply':'Принято!'})
        self.assertEqual(courses.overview(server,self.student)['messages'][0]['reply'],'Принято!')

    def test_content_edits_and_material_integrity(self):
        self.purchase()
        source=courses.content(server,self.student,'1')
        self.assertNotIn('data:image/png;base64,',source)
        blocks=courses.content(server,self.admin,'1',True)
        courses.action(server,self.admin,{'action':'lesson','id':1,'data':{'texts':{blocks[0]['id']:'<script>alert(1)</script>'}}})
        self.assertIn('&lt;script&gt;',courses.content(server,self.student,'1'))
        for lesson in courses.overview(server,self.admin,True)['lessons']:
            self.assertTrue(lesson['homework']);self.assertGreaterEqual(len(lesson['checklist']),3)
        with self.assertRaisesRegex(ValueError,'ссылка для просмотра'):
            courses.video_url('https://vkvideo.ru/video-123_456')
        with self.assertRaises(ValueError): courses.video_url('https://example.com/video-123_456')
        with self.assertRaises(ValueError): courses.action(server,self.admin,{'action':'settings','data':{'chat':'javascript:alert(1)'}})
        with self.assertRaises(ValueError): courses.action(server,self.admin,{'action':'lesson','id':1,'data':{'videos':['https://vkvideo.ru/video-1_2','https://vkvideo.ru/video-1_3']}})
        with self.assertRaises(LookupError): courses.media_file(server,self.student,'../server.py')

    def test_every_lesson_and_branch_loads(self):
        for resource in ['map',*[str(i) for i in range(1,8)],*[f'extra-{i}' for i in range(5)]]:
            source=courses.content(server,self.admin,resource)
            self.assertIn('<html',source.lower())
            self.assertNotIn('data:image/png;base64,',source)
        # External VK videos do not require shipping local MP4 recordings.
        if not (courses.SOURCE/courses.MEDIA[0]).is_file():
            with self.assertRaises(LookupError):courses.media_file(server,self.admin,'0',True)
        import re
        for filename in courses.FILES+courses.EXTRAS+['karta_kursa_vizual.html']:
            for name in re.findall(r'/api/courses/asset\?id=([a-f0-9]{64}\.[a-z]+)',(courses.SOURCE/filename).read_text('utf-8')):
                self.assertTrue(courses.media_file(server,self.admin,name).is_file(),name)

    def test_cart_entitlement_and_pending_payment(self):
        with server.db() as con:
            con.execute("INSERT INTO shop_orders(order_uid,product_id,product_title,amount,currency,buyer_email,status,created_at) VALUES ('cart','other','Корзина','5100.00','RUB','student','pending',?)",(server.now_iso(),))
            con.execute("INSERT INTO shop_order_items(order_uid,product_id,product_title,amount,currency,snapshot_json) VALUES ('cart',?,'Курс','5000.00','RUB','{}')",(courses.PRODUCT,))
        with self.assertRaises(PermissionError): courses.overview(server,self.student)
        with server.db() as con: con.execute("UPDATE shop_orders SET status='paid' WHERE order_uid='cart'")
        self.assertTrue(courses.overview(server,self.student)['lessons'][0]['available'])

    def test_user_deletion_cleans_course_records(self):
        self.purchase()
        courses.action(server,self.student,{'action':'progress','lesson_id':1,'data':{'completed':True}})
        courses.action(server,self.student,{'action':'message','lesson_id':1,'body':'Вопрос'})
        courses.action(server,self.admin,{'action':'homework','user_id':self.student['user_id'],'lesson_id':1,'completed':True})
        with server.db() as con:
            server.delete_user_records(con,self.student['user_id'])
            for table in ('course_members','course_progress','course_messages','course_homework'):
                self.assertEqual(con.execute(f'SELECT count(*) FROM {table}').fetchone()[0],0)

    def test_catalog_edit_keeps_delivery_and_gallery_and_is_admin_only(self):
        with self.assertRaises(PermissionError):
            courses.action(server,self.student,{'action':'catalog','data':{'amount':'1'}})
        before=courses.overview(server,self.admin,True)['product']
        courses.action(server,self.admin,{'action':'catalog','data':{'amount':'5000','sale_amount':'3000','sale_ends_at':'2099-12-01T12:00:00+03:00','shortDescription':'Новое краткое описание'}})
        after=courses.overview(server,self.admin,True)['product']
        self.assertEqual(after['delivery_url'],before['delivery_url'])
        self.assertEqual(after['cover_url'],before['cover_url'])
        self.assertEqual(after['description']['images'],before['description']['images'])
        self.assertEqual(after['description']['shortDescription'],'Новое краткое описание')
        self.assertEqual(after['sale_amount'],'3000.00')
        self.assertEqual(courses.video_url('<iframe src="https://vk.com/video_ext.php?oid=-12&amp;id=34"></iframe>'),'https://vk.com/video_ext.php?oid=-12&id=34')

    def test_payment_assigns_intake_group_and_does_not_move_existing_buyers(self):
        for gid in ('a','b'):
            courses.action(server,self.admin,{'action':'group','id':gid,'title':gid,'chat':'https://example.com/chat-'+gid,'schedule':{'2':'manual' if gid=='a' else ''}})
        courses.action(server,self.admin,{'action':'settings','data':{'default_group':'a'}})
        with server.db() as con:
            con.execute("INSERT INTO shop_orders(order_uid,product_id,product_title,amount,currency,buyer_email,status,created_at,yookassa_payment_id) VALUES ('confirmed-course',?,'Курс','5000.00','RUB','student','pending',?,'payment-course')",(courses.PRODUCT,server.now_iso()))
        payment={'id':'payment-course','status':'succeeded','amount':{'value':'5000.00','currency':'RUB'},'metadata':{'order_uid':'confirmed-course','product_id':courses.PRODUCT}}
        with patch.object(server,'yookassa_env',return_value=('shop','key','')),patch.object(server,'get_yookassa_payment',return_value=payment),patch.object(server,'attempt_order_delivery',return_value={'ok':True,'status':'paid'}):
            server.deliver_product_order('confirmed-course','payment-course')
        with server.db() as con:
            self.assertEqual(con.execute('SELECT group_id FROM course_members WHERE user_id=?',(self.student['user_id'],)).fetchone()[0],'a')
        courses.action(server,self.admin,{'action':'settings','data':{'default_group':'b'}})
        self.purchase(self.teacher)
        a=courses.overview(server,self.student)
        b=courses.overview(server,self.teacher)
        self.assertEqual(a['group']['id'],'a');self.assertEqual(b['group']['id'],'b')
        self.assertEqual(a['settings']['chat'],'https://example.com/chat-a')
        self.assertEqual(b['settings']['chat'],'https://example.com/chat-b')
        self.assertFalse(a['lessons'][1]['available']);self.assertTrue(b['lessons'][1]['available'])
        with self.assertRaises(ValueError):courses.action(server,self.admin,{'action':'settings','data':{'default_group':'missing'}})

    def test_guest_payment_remembers_group_before_registration(self):
        for gid in ('a','b'):courses.action(server,self.admin,{'action':'group','id':gid,'title':gid,'schedule':{}})
        courses.action(server,self.admin,{'action':'settings','data':{'default_group':'a'}})
        with server.db() as con:
            con.execute("INSERT INTO shop_orders(order_uid,product_id,product_title,amount,currency,buyer_email,status,created_at) VALUES ('late',?,'Курс','5000.00','RUB','late@example.com','paid',?)",(courses.PRODUCT,server.now_iso()))
            courses.record_paid_order(con,'late',server)
        courses.action(server,self.admin,{'action':'settings','data':{'default_group':'b'}})
        with server.db() as con,patch.object(server,'PASSWORD_HASH_ITERATIONS',1):
            server.seed_user(con,'late@example.com','password','student','Поздняя регистрация')
            user=dict(con.execute("SELECT * FROM users WHERE username='late@example.com'").fetchone())
        self.assertEqual(courses.overview(server,user)['group']['id'],'a')

    def test_homework_progress_is_admin_controlled_and_reversible(self):
        self.purchase();self.purchase(self.teacher)
        courses.overview(server,self.student)
        courses.action(server,self.student,{'action':'progress','lesson_id':1,'data':{'completed':True}})
        self.assertEqual(courses.overview(server,self.student)['homework_progress']['completed'],0)
        payload={'action':'homework','user_id':self.student['user_id'],'lesson_id':1,'completed':True}
        with self.assertRaises(PermissionError):courses.action(server,self.student,payload)
        courses.action(server,self.admin,payload)
        result=courses.overview(server,self.student)
        self.assertEqual(result['homework_progress'],{'completed':1,'total':7,'percent':14})
        self.assertEqual(courses.overview(server,self.teacher)['homework'],[])
        courses.action(server,self.admin,{**payload,'completed':False})
        self.assertEqual(courses.overview(server,self.student)['homework_progress']['completed'],0)
        with self.assertRaises(ValueError):courses.action(server,self.admin,{**payload,'lesson_id':8})
        with self.assertRaises(ValueError):courses.action(server,self.admin,{**payload,'completed':'false'})

    def test_shop_registration_and_refund_survive_description_edits(self):
        product=courses.overview(server,self.admin,True)['product']
        self.assertIn('Учитель',product['description']['registration'])
        self.assertIn('anastasia@dimitrieva-av.ru',product['description']['refund'])
        self.assertIn('возврат',product['description']['refund'])
        server.update_paid_entity_description(self.admin,{'product_id':courses.PRODUCT,'description':{'shortDescription':'Правка'}})
        edited=courses.overview(server,self.admin,True)['product']
        self.assertEqual(edited['description']['refund'],product['description']['refund'])
        self.assertEqual(edited['description']['images'],product['description']['images'])

    def test_vk_view_link_is_not_guessed_and_embed_access_parameters_survive(self):
        embed='https://vkvideo.ru/video_ext.php?oid=-243247388&id=456239018&hash=testhash&list=ln-osflaWTnhC8Zvj4l1a&hd=2'
        courses.action(server,self.admin,{'action':'lesson','id':1,'data':{'videos':[embed]}})
        view='https://vkvideo.ru/video-243247388_456239018?list=ln-osflaWTnhC8Zvj4l1a'
        with self.assertRaisesRegex(ValueError,'ссылка для просмотра'):
            courses.action(server,self.admin,{'action':'lesson','id':1,'data':{'videos':[view]}})
        self.assertEqual(courses.overview(server,self.admin,True)['lessons'][0]['videos'],[embed])
        self.assertEqual(courses.video_url('<iframe src="'+embed.replace('&','&amp;')+'"></iframe>'),embed)

    def test_first_lesson_two_video_slots_survive_restart_and_removal(self):
        videos=['https://vk.ru/video_ext.php?oid=-12&id=34&hash=one','https://vk.ru/video_ext.php?oid=-12&id=35&hash=two']
        courses.action(server,self.admin,{'action':'lesson','id':1,'data':{'videos':videos}})
        with server.db() as con: courses.seed(con,server)
        self.assertEqual(courses.overview(server,self.admin,True)['lessons'][0]['videos'],videos)
        courses.action(server,self.admin,{'action':'lesson','id':1,'data':{'videos':['',videos[1]]}})
        self.assertEqual(courses.overview(server,self.admin,True)['lessons'][0]['videos'],['',videos[1]])
        with self.assertRaises(ValueError):
            courses.action(server,self.admin,{'action':'lesson','id':2,'data':{'videos':videos}})
        with self.assertRaises(ValueError):
            courses.action(server,self.admin,{'action':'lesson','id':1,'data':{'videos':videos+videos}})

    def test_infographics_require_purchase_and_are_packaged(self):
        name=next(iter(courses.INFOGRAPHICS))
        with self.assertRaises(PermissionError):courses.media_file(server,self.student,name)
        self.purchase()
        for name in courses.INFOGRAPHICS:
            self.assertTrue(courses.media_file(server,self.student,name).is_file())
        with self.assertRaises(LookupError):courses.media_file(server,self.student,'../../server.py')

    def test_confirmed_course_payment_delivers_email_and_opens_access(self):
        email='course-buyer@example.test'
        with server.db() as con:
            con.execute('UPDATE users SET email=? WHERE user_id=?',(email,self.student['user_id']))
        self.student['email']=email
        with patch.object(server,'yookassa_env',return_value=('shop','secret','')),patch.object(server,'create_yookassa_payment',return_value={'id':'course-payment','confirmation':{'confirmation_url':'https://pay.test'}}):
            server.create_product_payment({'email':email,'products':['neurovisual']})
        with server.db() as con: uid=con.execute('SELECT order_uid FROM shop_orders').fetchone()[0]
        payment={'id':'course-payment','status':'succeeded','amount':{'value':'5000.00','currency':'RUB'},'metadata':{'order_uid':uid,'product_id':courses.PRODUCT}}
        with patch.object(server,'yookassa_env',return_value=('shop','secret','')),patch.object(server,'get_yookassa_payment',return_value=payment),patch.object(server,'send_order_email') as mail:
            result=server.confirm_order_return({'order_uid':uid})
            self.assertEqual(result['status'],'paid')
            self.assertTrue(result['email_sent'])
            mail.assert_called_once()
        self.assertTrue(courses.overview(server,self.student)['lessons'][0]['available'])

    def test_payment_return_uses_configured_domain(self):
        product=server.product_by_slug('neurovisual')
        with patch.object(server,'APP_BASE_URL','https://course.example.test'),patch.object(server,'yookassa_api_request',return_value={}) as api:
            server.create_yookassa_payment('shop','secret',product,'order-test','buyer@example.test')
        self.assertEqual(api.call_args.args[3]['confirmation']['return_url'],'https://course.example.test/shop/thanks?order=order-test')

    def test_consultation_email_does_not_depend_on_max_probe(self):
        with patch.object(server,'yookassa_env',return_value=('shop','secret','')),patch.object(server,'create_yookassa_payment',return_value={'id':'consult-payment','confirmation':{'confirmation_url':'https://pay.test'}}):
            server.create_product_payment({'email':'consult-buyer@example.test','products':['personal-consultation']})
        with server.db() as con: uid=con.execute('SELECT order_uid FROM shop_orders').fetchone()[0]
        payment={'id':'consult-payment','status':'succeeded','amount':{'value':'2000.00','currency':'RUB'},'metadata':{'order_uid':uid,'product_id':'personal-consultation'}}
        with patch.object(server,'yookassa_env',return_value=('shop','secret','')),patch.object(server,'get_yookassa_payment',return_value=payment),patch.object(server,'send_order_email') as mail,patch.object(server,'validate_delivery_link',side_effect=ValueError('MAX blocks server requests')) as probe:
            result=server.confirm_order_return({'order_uid':uid})
            self.assertTrue(result['email_sent'])
            probe.assert_not_called()
            mail.assert_called_once()


if __name__=='__main__':unittest.main()
