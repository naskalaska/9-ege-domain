import random
import unittest
import test_learning as fixtures
import server
import learning_module as learning
import statistics_module as statistics
from exam_variants import vary_row_answers


class LineLettersTest(unittest.TestCase):
    def setUp(self):
        self.case = fixtures.LearningTest()
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)

    def test_required_letters_checks_rows_and_letters_and_saves_draft(self):
        for activity in ('ege9','ege10','ege11','ege12'):
            with self.subTest(activity=activity):
                test = self.case.create({'activity':activity,'mode':'line','count':1,'require_letters':True})
                snap = self.case.snapshots(test['id'])[0]
                base = {'test_id':test['id'],'question_id':snap['question_id']}
                question = snap['question']
                key = question['correct_answer']
                self.assertTrue(learning.open_test(server,self.case.student,base)['questions'][0]['require_letters'])
                with self.assertRaises(ValueError):
                    learning.check_question(server,self.case.student,{**base,'answer':key})
                with self.assertRaises(ValueError):
                    learning.save_answers(server,self.case.student,{**base,'answers':{snap['question_id']:key}},submit=True)
                module = server if activity == 'ege9' else getattr(server,activity+'_module')
                ids = question.get('row_word_ids') or [r['word_ids'] for r in question['line_rows']]
                letters = {str(i):module.WORD_BY_ID[word_id]['correct_letter'] for i,word_id in enumerate(w for row in ids for w in row)}
                answer = {'rows':key,'letters':letters}
                learning.save_answers(server,self.case.student,{**base,'answers':{snap['question_id']:answer}})
                self.assertEqual(learning.open_test(server,self.case.student,base)['answers'][snap['question_id']],answer)
                # A correct row selection must still fail when a required letter is wrong.
                letters['0'] = 'я' if letters['0'] != 'я' else 'а'
                result = learning.check_question(server,self.case.student,{**base,'answer':answer})['checked_result']
                self.assertFalse(result['is_correct'])
                self.assertEqual(result['correct_answer'],key)
                self.assertFalse(result['letter_results'][0]['is_correct'])
                self.assertEqual(len(result['letter_results']),sum(map(len,ids)))
                self.assertEqual(statistics.overview(server,self.case.student,{'activity':activity})['summary']['correct'],0)
                teacher = learning.test_results(server,self.case.teacher,{**base,'student_id':self.case.student['user_id']})
                self.assertEqual(teacher['items'][0]['letter_results'],result['letter_results'])
                main = statistics.history(server,self.case.student,{'kind':'answers','activity':activity})['items'][0]
                self.assertFalse(main['is_correct'])
                self.assertEqual(main['letter_results'],result['letter_results'])
                self.assertIn(ids[0][0],{w['id'] for w in module.error_bank_words(self.case.student['user_id'])})

    def test_all_letters_correct_and_legacy_numeric_answers(self):
        test = self.case.create({'activity':'ege9','mode':'line','count':1,'require_letters':True})
        snap = self.case.snapshots(test['id'])[0]
        ids = [w for row in snap['question']['row_word_ids'] for w in row]
        answer = {'rows':snap['question']['correct_answer'],'letters':{str(i):server.WORD_BY_ID[w]['correct_letter'] for i,w in enumerate(ids)}}
        result = learning.check_question(server,self.case.student,{'test_id':test['id'],'question_id':snap['question_id'],'answer':answer})
        self.assertTrue(result['checked_result']['is_correct'])
        self.assertEqual(result['result']['correct'],1)
        test = self.case.create({'activity':'ege11','mode':'line','count':1})
        snap = self.case.snapshots(test['id'])[0]
        self.assertTrue(learning.check_question(server,self.case.student,{'test_id':test['id'],'question_id':snap['question_id'],
            'answer':snap['question']['correct_answer']})['checked_result']['is_correct'])

    def test_exam_series_keys_vary_and_metadata_matches(self):
        saved = random.getstate()
        self.addCleanup(random.setstate,saved)
        random.seed(20261020)
        for activity,mode in [('ege9','line'),('ege10','line'),('ege11','line'),('ege12','line'),('ege13','line_ne'),('ege14','exam')]:
            with self.subTest(activity=activity):
                test = self.case.create({'activity':activity,'mode':mode,'count':20})
                snaps = self.case.snapshots(test['id'])
                keys = [s['question']['correct_answer'] for s in snaps]
                self.assertTrue(all(a != b for a,b in zip(keys,keys[1:])))
                self.assertGreater(len(set(keys)),3)
                module = server if activity == 'ege9' else getattr(server,activity+'_module')
                for snap in snaps:
                    q = snap['question']
                    if activity in ('ege9','ege10','ege11','ege12'):
                        ids = q.get('row_word_ids') or [r['word_ids'] for r in q['line_rows']]
                        computed = ''.join(str(i+1) for i,row in enumerate(ids) if len({module.WORD_BY_ID[w]['correct_letter'] for w in row})==1)
                        self.assertEqual(q['correct_answer'],computed)
                        self.assertEqual(q['rows'],[[module.WORD_BY_ID[w]['variant'] for w in row] for row in ids])
                    else:
                        self.assertEqual(q['rows'],snap['public']['rows'])
                        if activity == 'ege13':
                            target = 'раздельно' if 'РАЗДЕЛЬНО' in q['prompt'] else 'слитно'
                            computed = ''.join(str(i+1) for i,w in enumerate(q['line_items']) if module.WORD_BY_ID[w]['answer']==target)
                        else:
                            target = module.instruction_target(q['prompt'])
                            computed = ''.join(str(i+1) for i,r in enumerate(q['exam_rows'])
                                if all(module.WORD_BY_ID[w]['answer']==target for w in r['item_ids']))
                        self.assertEqual(q['correct_answer'],computed)

    def test_task5_and_task15_variants_are_not_constant(self):
        positions = {server.ege5_module.make_exam_question()['_correct_answer'].split('|')[0] for _ in range(100)}
        self.assertEqual(positions,set('12345'))
        module = server.ege15_module
        patterns = set()
        for group in module.SENTENCES:
            q = module.sentence_question(group)
            visible = [part['target']['id'] for part in q['parts'] if 'target' in part]
            self.assertEqual(set(visible),set(q['_correct_answer']))
            patterns.add(tuple(q['_correct_answer'][word_id] for word_id in visible))
        self.assertGreater(len(patterns),1)


if __name__ == '__main__':
    unittest.main()
