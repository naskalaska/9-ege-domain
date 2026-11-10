import json
import unittest
from unittest.mock import patch
import server
import ege_speech_engine as engine
import ege_speech_module as speech
import learning_module as learning
import statistics_module as statistics
import test_learning as fixtures

class SpeechTest(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.LearningTest()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.teacher,self.student=self.fixture.teacher,self.fixture.student
        p=patch.object(engine,'DB_PATH',self.fixture.path)
        p.start();self.addCleanup(p.stop)

    def test_all_modes_private_keys_and_idempotent_results(self):
        for m in [speech.ege4,speech.ege6,speech.ege7,speech.ege8]:
            for mode in m.modes:
                data=server.activity_post(m.slug,'start',self.student,dict(mode=mode,count=2))
                private=m.PRACTICE_SESSIONS[data['session_id']]['questions']
                self.assertTrue(data['questions'])
                for q in data['questions']:
                    self.assertNotIn('correct_answer',q)
                    self.assertNotIn('explanation',q)
                answers={k:q['correct_answer'][0] if isinstance(q['correct_answer'],list) else q['correct_answer'] for k,q in private.items()}
                payload=dict(session_id=data['session_id'],answers=answers)
                result=server.activity_post(m.slug,'submit',self.student,payload)
                self.assertEqual(result['correct'],result['total'])
                self.assertEqual(result,server.activity_post(m.slug,'submit',self.student,payload))
                with self.assertRaises(ValueError):m.submit_practice(self.teacher,payload)
        stats=statistics.overview(server,self.student)
        self.assertEqual({r['activity'] for r in stats['by_activity'] if r['total']},{'ege4','ege6','ege7','ege8'})

    def test_error_bank_three_reviews_and_ownership(self):
        m=speech.ege4
        data=m.start_practice(self.student,dict(mode='stress',count=1))
        q=m.PRACTICE_SESSIONS[data['session_id']]['questions'][data['questions'][0]['question_id']]
        wrong=next(str(i) for i,c in enumerate(q['prompt']) if c in 'аеёиоуыэюя' and str(i)!=q['correct_answer'])
        m.submit_practice(self.student,dict(session_id=data['session_id'],answers={q['question_id']:wrong}))
        for _ in range(3):
            data=m.start_practice(self.student,dict(mode='errors',count=1))
            q=next(iter(m.PRACTICE_SESSIONS[data['session_id']]['questions'].values()))
            m.submit_practice(self.student,dict(session_id=data['session_id'],answers={q['question_id']:q['correct_answer']}))
        with self.assertRaises(ValueError):m.start_practice(self.student,dict(mode='errors'))
        with self.assertRaises(ValueError):m.start_practice(self.teacher,dict(mode='errors'))

    def test_content_filters_context_and_exam_structure(self):
        self.assertEqual(len(speech.ege4.WORDS),236)
        for w in speech.ege4.WORDS:
            if w.get('context_required'):
                for mode in ['stress','truth']:
                    q=speech.stress_question(w,mode)
                    self.assertIn(w['training_context']['display'],q.get('context','')+q['prompt'])
        for _ in range(30):
            q=speech.grammar_question(None,'exam',speech.ege8.WORDS)
            self.assertEqual(len(q['types']),5)
            self.assertEqual(len(q['sentences']),9)
            self.assertEqual(len(set(q['correct_answer'].values())),5)
        self.assertEqual(len(speech.ege6.WORDS),86)
        raw={r['id']:r for r in speech.raw6['entries']}
        self.assertEqual(set(raw),set(speech.ege6.WORD_BY_ID))
        for word in speech.ege6.WORDS:
            self.assertEqual(word['accepted'],raw[word['id']]['answer']['accepted'])

    def test_immediate_check_records_only_current_question_and_is_retry_safe(self):
        for module in [speech.ege4,speech.ege6,speech.ege7,speech.ege8]:
            for mode in module.modes:
                data=module.start_practice(self.student,dict(mode=mode,count=3))
                questions=list(module.PRACTICE_SESSIONS[data['session_id']]['questions'].values())
                q=questions[0]
                answer=q['correct_answer'][0] if isinstance(q['correct_answer'],list) else q['correct_answer']
                payload=dict(session_id=data['session_id'],question_id=q['question_id'],answer=answer)
                with server.db() as con:before=con.execute('SELECT COUNT(*) FROM attempts').fetchone()[0]
                result=module.check_practice_answer(self.student,payload)
                self.assertTrue(result['is_correct'])
                self.assertEqual(result,module.check_practice_answer(self.student,payload))
                with server.db() as con:self.assertEqual(con.execute('SELECT COUNT(*) FROM attempts').fetchone()[0],before+1)
                with self.assertRaises(ValueError):module.check_practice_answer(self.teacher,payload)
                with self.assertRaises(ValueError):module.check_practice_answer(self.student,{**payload,'question_id':'unknown'})
                answers={q['question_id']:q['correct_answer'][0] if isinstance(q['correct_answer'],list) else q['correct_answer'] for q in questions[1:]}
                finished=module.submit_practice(self.student,dict(session_id=data['session_id'],answers=answers))
                self.assertEqual(finished['correct'],3)
                with server.db() as con:self.assertEqual(con.execute('SELECT COUNT(*) FROM attempts').fetchone()[0],before+3)

    def test_immediate_check_in_mix_and_final_retry(self):
        mix=server.ege_speech_mix_module
        data=mix.start_practice(self.student,dict(task_counts={'ege1':1,'ege2':1,'ege3':1,'ege4':2,'ege5':1,'ege6':2,'ege7':2,'ege8':1}))
        session=mix.PRACTICE_SESSIONS[data['session_id']]
        answers={}
        for activity,sub in session['sub_sessions'].items():
            module=server.ege1_3_module if activity in {'ege1','ege2','ege3'} else getattr(server,activity+'_module')
            private=module.PRACTICE_SESSIONS[sub['session_id']]['questions']
            for public,original in sub['question_ids']:
                key=private[original]['correct_answer']
                if activity=='ege5':
                    row,word=key.split('|',1);key={'row':row,'word':word}
                answers[public]=key[0] if isinstance(key,list) else key
        with server.db() as con:before=con.execute('SELECT COUNT(*) FROM attempts').fetchone()[0]
        for qid,answer in answers.items():
            payload=dict(session_id=data['session_id'],question_id=qid,answer=answer)
            result=mix.check_practice_answer(self.student,payload)
            self.assertTrue(result['is_correct'])
            self.assertEqual(result,mix.check_practice_answer(self.student,payload))
        result=mix.submit_practice(self.student,dict(session_id=data['session_id'],answers=answers))
        self.assertEqual(result['correct'],len(answers))
        with server.db() as con:self.assertEqual(con.execute('SELECT COUNT(*) FROM attempts').fetchone()[0],before+len(answers))

    def test_task6_requires_written_answer_for_every_card(self):
        for word in speech.ege6.WORDS:
            for mode in ['rule','exam']:
                q=speech.lexical_question(word,mode)
                self.assertEqual(q['kind'],'speech_input')
                self.assertNotIn('choices',q)
                self.assertEqual(q['correct_answer'],word['accepted'])
                public=speech.ege6.public_question(q)
                self.assertNotIn('correct_answer',public)
                self.assertNotIn('explanation',public)
        data=speech.ege6.start_practice(self.student,dict(mode='rule',count=1))
        q=next(iter(speech.ege6.PRACTICE_SESSIONS[data['session_id']]['questions'].values()))
        payload=dict(session_id=data['session_id'],question_id=q['question_id'])
        with self.assertRaises(ValueError):speech.ege6.check_practice_answer(self.student,{**payload,'answer':''})
        result=speech.ege6.check_practice_answer(self.student,{**payload,'answer':q['correct_answer'][0]})
        self.assertTrue(result['is_correct'])

    def test_task8_includes_entire_bank_and_counts_errors_separately(self):
        raw=[(norm,row) for norm,groups in speech.raw8['norms'].items() for rows in groups.values() if isinstance(rows,list) for row in rows]
        expected={f"ru8:{r['card_id']}:{r['sentence_number']}:{norm}" for norm,r in raw}
        self.assertEqual(set(speech.ege8.WORD_BY_ID),expected)
        self.assertEqual(len(speech.ege8.WORDS),769)
        self.assertEqual(sum(not w['is_correct'] for w in speech.ege8.WORDS),430)
        self.assertEqual(sum(w['is_correct'] for w in speech.ege8.WORDS),339)
        for norm,r in raw:
            word=speech.ege8.WORD_BY_ID[f"ru8:{r['card_id']}:{r['sentence_number']}:{norm}"]
            self.assertEqual(word['sentence'],r['sentence_text'])
            self.assertEqual(word['is_correct'],r['is_correct'])
            q=speech.grammar_question(word,'classify')
            self.assertEqual(q['correct_answer'],'none' if r['is_correct'] else norm)
        data=server.activity_bootstrap('ege8',self.student)
        self.assertEqual(data['error_sentence_count'],430)
        self.assertEqual(data['correct_sentence_count'],339)
        self.assertEqual(data['word_count'],769)

    def test_teacher_exports(self):
        for activity in ['ege4','ege6','ege7','ege8','speech-ege']:
            module=server.ege_speech_mix_module if activity=='speech-ege' else getattr(server,activity+'_module')
            body,name,mime=server.build_test_file(self.teacher,dict(activity=activity,mode='exam',count=1,task_counts={'ege2':1,'ege4':1,'ege5':1,'ege8':1}))
            self.assertIn('Ответы',body.decode())
            self.assertTrue(name.endswith('.txt'))
            with self.assertRaises(PermissionError):module.build_test_file(self.student,dict(mode='exam',count=1))

    def test_mix_exact_counts_and_assigned_frozen_checks(self):
        mix=server.ege_speech_mix_module
        counts=dict(ege1=1,ege2=2,ege3=1,ege4=1,ege5=1,ege8=1)
        data=mix.start_practice(self.student,dict(task_counts=counts))
        session=mix.PRACTICE_SESSIONS[data['session_id']]
        self.assertEqual(len(data['questions']),7)
        answers={}
        for activity,sub in session['sub_sessions'].items():
            module=server.ege1_3_module if activity in {'ege1','ege2','ege3'} else getattr(server,activity+'_module')
            private=module.PRACTICE_SESSIONS[sub['session_id']]['questions']
            for public,original in sub['question_ids']:
                q=private[original]
                key=q['correct_answer']
                if activity=='ege5':
                    row,word=key.split('|',1)
                    key={'row':row,'word':word}
                answers[public]=key[0] if isinstance(key,list) else key
        result=mix.submit_practice(self.student,dict(session_id=data['session_id'],answers=answers))
        self.assertEqual(result['correct'],7)
        self.assertEqual({r['question_id'] for r in result['results']},set(answers))
        self.assertEqual(result,mix.submit_practice(self.student,dict(session_id=data['session_id'],answers=answers)))
        for counts in [dict(ege4=0)]:
            with self.assertRaises(ValueError):mix.start_practice(self.student,dict(task_counts=counts))
        for activity,mode in [('ege4','stress'),('ege6','rule'),('ege7','truth'),('ege8','exam'),('speech-ege','ege_exam_mix')]:
            config=dict(activity=activity,mode=mode,count=1,task_counts={'ege2':1,'ege8':1})
            created=learning.create_test(server,self.teacher,dict(student_ids=[self.student['user_id']],config=config))
            opened=learning.open_test(server,self.student,dict(test_id=created['id']))
            with server.db() as con:
                snaps=json.loads(con.execute('SELECT questions_json FROM assigned_tests WHERE id=?',(created['id'],)).fetchone()[0])
            for snap in snaps:
                self.assertNotIn('correct_answer',snap['public'])
                answer=snap['question']['correct_answer']
                if isinstance(answer,list):answer=answer[0]
                self.assertTrue(learning.answer_complete(snap['question'],answer))
                with server.db() as con:
                    result=learning.record_check(server,con,self.student,dict(test_id=created['id']),snap,answer,1)
                self.assertTrue(result['is_correct'])

    def test_task7_complete_source_and_norm_only_forms(self):
        m=speech.ege7
        self.assertEqual(len(m.WORDS),420)
        self.assertEqual(set(m.WORD_BY_ID),{r['id'] for r in speech.raw7['phrase_pairs']})
        self.assertEqual(sum(bool(w.get('incorrect_variant')) for w in m.WORDS),371)
        for w in m.WORDS:
            for mode in ['fix','truth','choice']:
                if not w.get('incorrect_variant') and mode in {'fix','choice'}:
                    with self.assertRaises(ValueError):speech.morphology_question(w,mode)
                    continue
                q=speech.morphology_question(w,mode)
                answer=q['correct_answer']
                if isinstance(answer,list): answer=answer[0].lower()
                self.assertTrue(m.answer_complete(q,answer))
                self.assertTrue(m.grade(q,answer)[0],w['id'])
                if not w.get('incorrect_variant'):
                    self.assertNotIn('None',q['prompt'])
                    if mode=='fix': self.fail('Norm-only form entered fix mode')
                    if mode=='truth': self.assertEqual(answer['verdict'],'true')
        for rule,pool in m.WORDS_BY_RULE.items():
            for mode in ['fix','truth','choice','exam']:
                questions=m.select_questions(self.student,dict(mode=mode,count=2,rule_ids=[rule]))
                for q in questions:
                    self.assertEqual(q['rule_id'],rule)
                    if mode in {'fix','choice'}:
                        source=m.WORD_BY_ID[q['source_word_id']]
                        self.assertTrue(source['incorrect_variant'])
                        if mode=='fix':self.assertEqual(q['prompt'],source['incorrect_variant'])
                        else:self.assertEqual({c['value'] for c in q['choices']},{source['correct_variant'],source['incorrect_variant']})
                    if mode=='exam':
                        self.assertEqual(len(q['prompt'].splitlines()),5)
                        target=m.WORD_BY_ID[q['source_word_id']]
                        self.assertIn(target['incorrect_variant'],q['prompt'])
                        self.assertEqual(q['correct_answer'],[target['highlighted_correct_form']])

    def test_task7_truth_requires_correct_verdict_and_written_correction(self):
        m=speech.ege7
        w=next(w for w in m.WORDS if w.get('incorrect_variant'))
        with patch.object(speech.random,'choice',return_value=False):
            q=speech.morphology_question(w,'truth')
        self.assertFalse(m.answer_complete(q,{'verdict':'false','word':''}))
        self.assertFalse(m.grade(q,{'verdict':'true'})[0])
        self.assertFalse(m.grade(q,{'verdict':'false','word':'ошибка'})[0])
        self.assertTrue(m.grade(q,{'verdict':'false','word':w['highlighted_correct_form'].lower()})[0])

    def test_task7_error_reviews_and_group_bank_coverage(self):
        m=speech.ege7
        data=m.start_practice(self.student,dict(mode='fix',count=1))
        q=next(iter(m.PRACTICE_SESSIONS[data['session_id']]['questions'].values()))
        key=q['correct_answer'][0]
        def check(data,q,answer):
            return m.check_practice_answer(self.student,dict(session_id=data['session_id'],question_id=q['question_id'],answer=answer))
        check(data,q,key)
        data7=server.activity_bootstrap('ege7',self.student)
        self.assertEqual(data7['bank_progress'],{'total':420,'solved':1})
        self.assertEqual(data7['rule_progress'][q['rule_id']]['solved'],1)
        data=m.start_practice(self.student,dict(mode='fix',count=1,rule_ids=[q['rule_id']]))
        private=m.PRACTICE_SESSIONS[data['session_id']]
        private['questions']={q['question_id']:q}
        check(data,q,'ошибка')
        self.assertEqual(server.activity_bootstrap('ege7',self.student)['bank_progress']['solved'],0)
        for remaining in [2,1,0]:
            data=m.start_practice(self.student,dict(mode='errors',count=1))
            retry=next(iter(m.PRACTICE_SESSIONS[data['session_id']]['questions'].values()))
            self.assertEqual(retry['source_word_id'],q['source_word_id'])
            check(data,retry,retry['correct_answer'][0])
            with server.db() as con:
                due=con.execute('SELECT due_reviews FROM word_progress WHERE user_id=? AND scope_id=? AND word_id=?',(self.student['user_id'],m.scope_id_for('errors'),q['source_word_id'])).fetchone()[0]
            self.assertEqual(due,remaining)
        self.assertEqual(server.activity_bootstrap('ege7',self.student)['bank_progress']['solved'],1)
        with self.assertRaises(ValueError): m.start_practice(self.student,dict(mode='errors'))

    def test_task7_teacher_every_mode_print_and_frozen_assignment(self):
        m=speech.ege7
        for mode in m.modes:
            config=dict(activity='ege7',mode=mode,count=3)
            body,_,_=server.build_test_file(self.teacher,config)
            self.assertIn('Ответы',body.decode())
            if mode=='choice': self.assertIn('2)',body.decode())
            created=learning.create_test(server,self.teacher,dict(student_ids=[self.student['user_id']],config=config))
            opened=learning.open_test(server,self.student,dict(test_id=created['id']))
            with server.db() as con:
                snaps=json.loads(con.execute('SELECT questions_json FROM assigned_tests WHERE id=?',(created['id'],)).fetchone()[0])
            for q,snap in zip(opened['questions'],snaps):
                self.assertNotIn('source_word_id',q)
                self.assertNotIn('correct_answer',q)
                answer=snap['question']['correct_answer']
                if isinstance(answer,list):answer=answer[0]
                result=learning.check_question(server,self.student,dict(test_id=created['id'],question_id=q['question_id'],answer=answer))
                self.assertTrue(result['checked_results'][q['question_id']]['is_correct'])
        report=statistics.overview(server,self.student)
        row=next(r for r in report['by_activity'] if r['activity']=='ege7')
        self.assertEqual(row['total'],12)
        self.assertEqual(row['correct'],12)

    def test_all_banks_coverage_and_task5_teacher_modes(self):
        self.assertEqual(set(speech.ege4.WORD_BY_ID),{w['id'] for w in speech.stress_bank['words']})
        source5=json.loads(server.ege5_module.DATA_PATH.read_text(encoding='utf8'))
        self.assertEqual({r['id'] for r in server.ege5_module.ROWS},{r['row_id'] for r in source5['rows']})
        for activity in ['ege1-3','ege4','ege5','ege6','ege7','ege8']:
            data=server.activity_bootstrap(activity,self.student)
            self.assertEqual(data['bank_progress']['total'],sum(g['total'] for g in data['rule_progress'].values()))
            self.assertEqual(sum(g['total'] for g in data['category_progress'].values()),data['bank_progress']['total'])
        m=server.ege5_module
        for mode in ['paronym_choice','paronym_tf','paronym_exam']:
            config=dict(activity='ege5',mode=mode,count=2,rule_ids=[r['rule_id'] for r in m.RULES])
            body,_,_=server.build_test_file(self.teacher,config)
            self.assertIn('Ответы',body.decode())
            if mode=='paronym_tf':self.assertIn('Верно или неверно?',body.decode())
            created=learning.create_test(server,self.teacher,dict(student_ids=[self.student['user_id']],config=config))
            with server.db() as con:snaps=json.loads(con.execute('SELECT questions_json FROM assigned_tests WHERE id=?',(created['id'],)).fetchone()[0])
            for snap in snaps:
                key=snap['question']['correct_answer']
                if mode=='paronym_tf':
                    verdict,_,word=key.partition('|');key=dict(verdict=verdict,word=word)
                elif mode=='paronym_exam':
                    row,word=key.split('|',1);key=dict(row=row,word=word)
                result=learning.check_question(server,self.student,dict(test_id=created['id'],question_id=snap['question_id'],answer=key))
                self.assertTrue(result['checked_results'][snap['question_id']]['is_correct'])

if __name__=='__main__':unittest.main()
