import concurrent.futures
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import ege1_3_module as lab
import learning_module as learning
import server
import statistics_module as statistics
import student_workspace as workspace
import test_learning as fixtures


class TextLabTest(unittest.TestCase):
    def setUp(self):
        self.case = fixtures.LearningTest()
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.teacher, self.student = self.case.teacher, self.case.student
        lab.PRACTICE_SESSIONS.clear()
        self.addCleanup(lab.PRACTICE_SESSIONS.clear)

    def config(self, mode='gap', count=1, **extra):
        return {'activity': 'ege1-3', 'mode': mode, 'count': count, **extra}

    def answer(self, q):
        value = q.get('correct_answer', q.get('_correct_answer'))
        return value[0] if isinstance(value, list) else value

    def wrong(self, q):
        if q['kind'] == 'text_lab_bool':
            return 'false' if self.answer(q) == 'true' else 'true'
        return 'ошибочный ответ' if q['kind'] == 'text_lab_gap' else ('1' if self.answer(q) != '1' else '2')

    def attempt_count(self):
        with server.db() as con:
            return con.execute('SELECT COUNT(*) FROM attempts').fetchone()[0]

    def assert_public(self, q):
        def walk(item):
            if isinstance(item, dict):
                self.assertFalse({'answer', 'correct_answer', '_correct_answer', 'valid', 'why', 'right', 'explanation'} & item.keys())
                for v in item.values(): walk(v)
            elif isinstance(item, list):
                for v in item: walk(v)
        walk(q)
        if q['task_number'] == 3:
            self.assertNotIn('rule_id', q)
            self.assertEqual(q['rule_name'], 'Характеристики текста')

    def test_base_keys_topics_highlights_and_catalogue(self):
        source = json.loads((server.ROOT / 'task_1_3_content_fixed_v32.json').read_text(encoding='utf-8'))
        self.assertEqual(len(lab.ENTRIES), 86)
        self.assertEqual(len(lab.WORD_BY_ID), len(lab.WORDS))
        for raw, entry in zip(source['entries'], lab.ENTRIES):
            self.assertEqual(raw['shared_context']['text'], entry['text'])
            for task in raw['tasks']:
                normalized = entry['tasks'][str(task['number'])]
                self.assertEqual(task['valid_answers'], normalized['valid'])
                if task['number'] > 1:
                    self.assertEqual([o['correct_according_to_published_key'] for o in task['structured']['options']],
                                     [o['right'] for o in normalized['options']])
        missing = [(e['id'], o['lemma']) for e in lab.ENTRIES for o in e['tasks']['2']['options'] if not o['range']]
        self.assertEqual(len(missing), 1)
        self.assertEqual(missing[0][1].lower(), 'точка')
        for word in lab.WORDS:
            if word['task_number'] == 2:
                self.assertTrue(word['highlight_ranges'])
                for a, b in word['highlight_ranges']:
                    self.assertTrue(word['text'][a:b].strip())
        data = server.activity_bootstrap('ege1-3', self.student)
        self.assertEqual(data['word_count'], 86)
        self.assertIn('ege1-3', {a['slug'] for a in data['activities']})
        self.assertEqual(set(data['rules']), {'Задание 1', 'Задание 2', 'Задание 3'})
        self.assertEqual(len(data['rules']['Задание 3']), 5)

    def test_every_mode_server_grading_and_no_keys_before_check(self):
        for mode in ('gap', 'lex', 'truth', 'characteristics', 'exam'):
            with self.subTest(mode=mode):
                started = server.activity_post('ege1-3', 'start', self.student, self.config(mode, 2))
                private = lab.PRACTICE_SESSIONS[started['session_id']]['questions']
                self.assertEqual(len(private), 6 if mode == 'exam' else 2)
                for public in started['questions']: self.assert_public(public)
                answers = {qid: self.answer(q) for qid, q in private.items()}
                result = lab.submit_practice(self.student, {'session_id': started['session_id'], 'answers': answers})
                self.assertEqual(result['correct'], result['total'])
                count = self.attempt_count()
                self.assertEqual(lab.submit_practice(self.student, {'session_id': started['session_id'], 'answers': {}}), result)
                self.assertEqual(self.attempt_count(), count)

    def test_exam_keeps_three_questions_together_and_does_not_allow_partial_reveal(self):
        started = lab.start_practice(self.student, self.config('exam', 30))
        rows = started['questions']
        self.assertEqual(len(rows), 90)
        for i in range(0, len(rows), 3):
            self.assertEqual([q['task_number'] for q in rows[i:i+3]], [1, 2, 3])
            self.assertEqual(len({q['text'] for q in rows[i:i+3]}), 1)
        with self.assertRaises(ValueError):
            lab.check_practice_answer(self.student, {'session_id': started['session_id'], 'question_id': rows[0]['question_id'], 'answer': 'что'})
        with self.assertRaises(ValueError): lab.submit_practice(self.student, {'session_id': started['session_id'], 'answers': {}})
        self.assertEqual(self.attempt_count(), 0)

    def test_complete_set_free_text_and_boolean_validation(self):
        gap = next(w for w in lab.WORDS if w['kind'] == 'text_lab_gap' and len(w['answer']) > 1)
        q = {**lab.word_question(gap), 'correct_answer': gap['answer']}
        for valid in gap['answer']:
            self.assertTrue(lab.grade(q, '  ' + valid.upper() + '  ')[0])
        multi = {**lab.word_question(next(w for w in lab.WORDS if w['kind'] == 'text_lab_multi'))}
        multi['correct_answer'] = multi.pop('_correct_answer')
        key = multi['correct_answer']
        self.assertTrue(lab.grade(multi, key[::-1])[0])
        self.assertFalse(lab.grade(multi, self.wrong(multi))[0])
        for invalid in (None, {}, [], '1x', '0', '123456', ''):
            self.assertFalse(lab.answer_complete(multi, invalid))
        boolean = lab.word_question(next(w for w in lab.WORDS if w['kind'] == 'text_lab_bool'))
        for invalid in (False, 0, None, {}, 'Верно', '1'):
            self.assertFalse(lab.answer_complete(boolean, invalid))

    def test_topic_filters_and_reject_unknown_topic(self):
        for mode, number in (('gap', 1), ('truth', 3), ('characteristics', 3)):
            rule = next(r for r in lab.RULES if r['category'] == f'Задание {number}')
            started = lab.start_practice(self.student, self.config(mode, 30, rule_ids=[rule['rule_id']]))
            private = lab.PRACTICE_SESSIONS[started['session_id']]['questions']
            self.assertTrue(all(q['rule_id'] == rule['rule_id'] for q in private.values()))
        with self.assertRaises(ValueError): lab.start_practice(self.student, self.config(rule_ids=['ege9:fake']))

    def test_concurrent_check_and_submit_are_idempotent_and_scoped(self):
        started = lab.start_practice(self.student, self.config())
        qid, q = next(iter(lab.PRACTICE_SESSIONS[started['session_id']]['questions'].items()))
        check = {'session_id': started['session_id'], 'question_id': qid, 'answer': self.answer(q)}
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            rows = list(pool.map(lambda _: lab.check_practice_answer(self.student, check), range(4)))
        self.assertTrue(all(r == rows[0] for r in rows))
        self.assertEqual(self.attempt_count(), 1)
        result = lab.submit_practice(self.student, {'session_id': started['session_id'], 'answers': {qid: self.wrong(q)}})
        self.assertEqual(result['correct'], 1)
        self.assertEqual(self.attempt_count(), 1)
        with self.assertRaises(ValueError): lab.submit_practice({**self.student, 'user_id': 'other'}, {'session_id': started['session_id']})
        with self.assertRaises(ValueError): lab.check_practice_answer(self.student, {**check, 'question_id': 'other'})

    def test_error_bank_requires_three_correct_repetitions_and_never_duplicates_rows(self):
        started = lab.start_practice(self.student, self.config('characteristics'))
        qid, q = next(iter(lab.PRACTICE_SESSIONS[started['session_id']]['questions'].items()))
        lab.check_practice_answer(self.student, {'session_id': started['session_id'], 'question_id': qid, 'answer': self.wrong(q)})
        for remaining in (2, 1, 0):
            self.assertEqual(len(lab.error_bank_words(self.student['user_id'])), 1)
            repeat = lab.start_practice(self.student, self.config('errors'))
            rqid, private = next(iter(lab.PRACTICE_SESSIONS[repeat['session_id']]['questions'].items()))
            self.assertEqual(private['kind'], 'text_lab_multi')
            payload = {'session_id': repeat['session_id'], 'question_id': rqid, 'answer': self.answer(private)}
            lab.check_practice_answer(self.student, payload)
            lab.check_practice_answer(self.student, payload)
            with server.db() as con:
                due = con.execute('SELECT due_reviews FROM word_progress WHERE user_id=? AND scope_id=? AND word_id=?',
                                  (self.student['user_id'], lab.scope_id_for('errors'), q['source_word_id'])).fetchone()[0]
            self.assertEqual(due, remaining)
        self.assertEqual(len(lab.error_bank_words(self.student['user_id'])), 0)
        self.assertEqual(self.attempt_count(), 4)
        with self.assertRaises(ValueError): lab.start_practice(self.student, self.config('errors'))

    def test_teacher_frozen_assignment_drafts_check_resume_report_calendar_revoke_and_access(self):
        group = learning.save_group(server, self.teacher, {'title': 'Тексты', 'student_ids': [self.student['user_id']]})
        test = learning.create_test(server, self.teacher, {'title': 'Текст', 'group_ids': [group['id']],
                                    'config': self.config('exam', 1), 'due_at': '2027-01-01T12:00:00+03:00'})
        snaps = self.case.snapshots(test['id'])
        self.assertEqual(len(snaps), 3)
        for snap in snaps: self.assert_public(snap['public'])
        opened = learning.open_test(server, self.student, {'test_id': test['id']})
        self.assertEqual(opened['outline'][0]['title'], 'Задания 1–3')
        answers = {s['question_id']: self.answer(s['question']) for s in snaps}
        learning.save_answers(server, self.student, {'test_id': test['id'], 'answers': answers})
        self.assertEqual(learning.open_test(server, self.student, {'test_id': test['id']})['answers'], answers)
        first = {'test_id': test['id'], 'question_id': snaps[0]['question_id'], 'answer': answers[snaps[0]['question_id']]}
        key = lab.WORD_BY_ID[snaps[0]['question']['source_word_id']]['answer']
        # The student's saved test keeps its old answer even if the source bank later changes.
        word = lab.WORD_BY_ID[snaps[0]['question']['source_word_id']]
        word['answer'] = ['changed-bank']
        try:
            checked = learning.check_question(server, self.student, first)
        finally:
            word['answer'] = key
        self.assertTrue(checked['checked_result']['is_correct'])
        self.assertEqual(learning.check_question(server, self.student, {**first, 'answer': 'changed'}), checked)
        report = learning.test_results(server, self.teacher, {'test_id': test['id'], 'student_id': self.student['user_id']})
        self.assertEqual((report['checked'], report['correct']), (1, 1))
        self.assertIn(snaps[0]['question']['text'].splitlines()[0], report['items'][0]['prompt'])
        self.assertEqual(len(workspace.calendar(server, self.student, {})['items']), 1)
        for user in (self.teacher, {**self.student, 'user_id': 'other'}):
            with self.assertRaises(PermissionError): learning.open_test(server, user, {'test_id': test['id']})
        with self.assertRaises(PermissionError): self.case.create(self.config(), student_ids=['other'])
        result = learning.save_answers(server, self.student, {'test_id': test['id'], 'answers': answers}, submit=True)
        self.assertEqual((result['correct'], result['total']), (3, 3))
        self.assertEqual(self.attempt_count(), 3)
        self.assertEqual(learning.save_answers(server, self.student, {'test_id': test['id'], 'answers': {}}, submit=True), result)
        self.assertEqual(self.attempt_count(), 3)
        other = self.case.create(self.config('characteristics'))
        learning.revoke_test(server, self.teacher, {'test_id': other['id']})
        with self.assertRaises(PermissionError): learning.open_test(server, self.student, {'test_id': other['id']})

    def test_class_errors_export_statistics_profile_and_history_repeat(self):
        started = lab.start_practice(self.student, self.config('truth'))
        qid, q = next(iter(lab.PRACTICE_SESSIONS[started['session_id']]['questions'].items()))
        lab.check_practice_answer(self.student, {'session_id': started['session_id'], 'question_id': qid, 'answer': self.wrong(q)})
        history = statistics.history(server, self.teacher, {'activity': 'ege1-3'})
        self.assertEqual(history['total'], 1)
        item = history['items'][0]
        self.assertTrue(item['can_repeat'])
        self.assertFalse(item['is_detail'])
        self.assertIn(q['statement'], item['prompt'])
        self.assertEqual(workspace.profile(server, self.teacher, {'student_id': self.student['user_id']})['statistics']['summary']['total'], 1)
        self.assertEqual(statistics.overview(server, self.student, {})['summary']['total'], 1)
        csv, _, _ = statistics.export(server, self.teacher, {'activity': 'ege1-3'})
        self.assertIn(q['statement'], csv.decode('utf-8-sig'))
        repeat = workspace.repeat_error(server, self.student, {'attempt_id': item['attempt_id']})
        snap = self.case.snapshots(repeat['id'])[0]
        self.assertEqual(snap['question']['kind'], 'text_lab_bool')
        checked = learning.check_question(server, self.student, {'test_id': repeat['id'], 'question_id': snap['question_id'], 'answer': self.answer(snap['question'])})
        self.assertTrue(checked['result']['correct'])
        class_test = self.case.create(self.config('errors', 5))
        self.assertEqual(class_test['total'], 1)
        txt, _, _ = server.build_test_file(self.teacher, self.config('errors', 5))
        self.assertIn(q['statement'], txt.decode())
        self.assertIn('Ответы', txt.decode())
        with self.assertRaises(ValueError): lab.select_questions({**self.teacher, 'user_id': 'other-teacher'}, self.config('errors'), teacher=True)
        with self.assertRaises(PermissionError): server.build_test_file(self.student, self.config())

    def test_http_catalogue_bootstrap_assignment_and_hidden_bank(self):
        http = ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        threading.Thread(target=http.serve_forever, daemon=True).start()
        self.addCleanup(http.server_close)
        self.addCleanup(http.shutdown)
        token = 'text-lab-http'
        server.SESSIONS[token] = {'user': self.student}
        self.addCleanup(lambda: server.SESSIONS.pop(token, None))
        base = f'http://127.0.0.1:{http.server_port}'
        def get(path, data=None, auth=True):
            headers = {'Authorization': 'Bearer ' + token} if auth else {}
            if data is not None: headers['Content-Type'] = 'application/json'
            return urlopen(Request(base+path, data=json.dumps(data).encode() if data is not None else None, headers=headers))
        html = get('/apps/ege1-3').read().decode()
        self.assertIn('/text-lab.js', html)
        self.assertIn('/text-lab.css', html)
        self.assertIn('ege1-3', {a['slug'] for a in json.load(get('/api/activities'))['activities']})
        self.assertEqual(json.load(get('/api/apps/ege1-3/bootstrap'))['word_count'], 86)
        started = json.load(get('/api/apps/ege1-3/practice/start', self.config('characteristics')))
        self.assert_public(started['questions'][0])
        for route in ('/task-1-3/bank.json', '/task_1_3_trainer_bank.json'):
            with self.assertRaises(HTTPError) as err: get(route)
            self.assertEqual(err.exception.code, 404)
        with self.assertRaises(HTTPError) as err: get('/api/apps/ege1-3/practice/start', self.config(), auth=False)
        self.assertEqual(err.exception.code, 401)


if __name__ == '__main__':
    unittest.main()
