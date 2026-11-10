"""Text lab: server-side grading, frozen assignments and the shared error bank."""
from __future__ import annotations

import hashlib
import json
import random
import re
import secrets
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from attempt_content import describe_question

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / 'data' / 'ege_app.db'
ACTIVITY = 'ege1-3'
REPEAT_ON_ERROR = 3
PRACTICE_SESSIONS = {}
SESSION_LOCK = threading.RLock()
MODES = ('gap', 'lex', 'truth', 'characteristics', 'exam', 'errors', 'task_exam_1', 'task_exam_2', 'task_exam_3')
SOURCE_LABEL = 'Тексты из сборников Р.А. Дощинского 2025, 2026 года'
# Generated from v32 by tools/build_task_1_3_demo.cjs; kept OUTSIDE static/.
ENTRIES = json.loads((ROOT / 'task_1_3_trainer_bank.json').read_text(encoding='utf-8'))


def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def rule_id(number, topic):
    return 'textlab:' + str(number) + ':' + hashlib.sha1(topic.encode()).hexdigest()[:12]


def scope_id_for(mode, rule_id=None, rule_ids=None):
    if mode == 'errors':
        return ACTIVITY + ':errors:bank'
    selected = sorted(set(rule_ids or ([rule_id] if rule_id else [])))
    return ACTIVITY + ':' + mode + (':rules:' + hashlib.sha1('|'.join(selected).encode()).hexdigest()[:12] if selected else '')


def build_words():
    words = []
    for entry in ENTRIES:
        for number in (1, 2, 3):
            task = entry['tasks'][str(number)]
            topic = entry['topic'] if number == 1 else entry['style'] if number == 3 else 'Значение слова в контексте'
            base = {'category': f'Задание {number}', 'rule_id': rule_id(number, topic), 'rule_name': topic,
                    'text': entry['text'], 'task_number': number, 'entry_id': entry['id']}
            if number == 1:
                words.append({**base, 'id': task['id'], 'kind': 'text_lab_gap', 'prompt': task['prompt'],
                              'answer': task['valid'], 'explanation': task['why'], 'options': [], 'highlight_ranges': []})
            else:
                for option in task['options']:
                    if number == 2 and not option['range']:
                        # v32 contains one dictionary headword absent from its context.
                        continue
                    words.append({**base, 'id': task['id'] + ':option:' + str(option['n']), 'kind': 'text_lab_bool',
                                  'prompt': ('Совпадает ли словарное толкование со значением выделенного слова в тексте?'
                                             if number == 2 else 'Верно ли утверждение об исходном тексте?'),
                                  'statement': option['text'], 'answer': 'true' if option['right'] else 'false',
                                  'explanation': option['why'], 'options': [],
                                  'highlight_ranges': [option['range']] if number == 2 else []})
                if number == 2 and not all(o['range'] for o in task['options']):
                    continue
                explanation = '\n\n'.join(f"{o['n']}. {'Верно' if o['right'] else 'Неверно'}: {o['why']}" for o in task['options'])
                words.append({**base, 'id': task['id'], 'kind': 'text_lab_multi', 'prompt': task['prompt'],
                              'answer': ''.join(str(o['n']) for o in task['options'] if o['right']),
                              'options': [{'n': o['n'], 'text': o['text']} for o in task['options']],
                              'explanation': explanation,
                              'highlight_ranges': [o['range'] for o in task['options']] if number == 2 else []})
    return words


WORDS = build_words()
WORD_BY_ID = {w['id']: w for w in WORDS}
WORDS_BY_RULE = {}
for _word in WORDS:
    WORDS_BY_RULE.setdefault(_word['rule_id'], []).append(_word)
RULES = [{'rule_id': rid, 'category': items[0]['category'], 'rule_name': items[0]['rule_name'],
          'count': len({i['entry_id'] for i in items})} for rid, items in WORDS_BY_RULE.items()]


def word_question(word):
    private = {'question_id': secrets.token_hex(12), 'source_word_id': word['id'],
               'kind': word['kind'], 'task_number': word['task_number'], 'text': word['text'],
               'prompt': word['prompt'], 'statement': word.get('statement', ''), 'options': word['options'],
               'highlight_ranges': word['highlight_ranges'], 'rule_id': word['rule_id'],
               'category': word['category'], 'rule_name': word['rule_name'],
               'explanation': word['explanation'], '_correct_answer': word['answer']}
    return private


def public_question(question):
    public = {k: v for k, v in question.items() if not k.startswith('_') and k not in {'correct_answer', 'explanation'}}
    if question['task_number'] == 3:
        # The true style is a reporting topic, not a hint before an answer.
        public.pop('rule_id', None)
        public['rule_name'] = 'Характеристики текста'
    return public


def error_bank_words(user_id):
    with db() as con:
        rows = con.execute('SELECT word_id FROM word_progress WHERE user_id=? AND scope_id=? AND due_reviews>0 ORDER BY last_seen_at',
                           (user_id, scope_id_for('errors'))).fetchall()
    return [WORD_BY_ID[r['word_id']] for r in rows if r['word_id'] in WORD_BY_ID]


def mode_pool(mode, config):
    selected = set(str(r) for r in config.get('rule_ids') or [])
    if selected - WORDS_BY_RULE.keys():
        raise ValueError('Неизвестная тема задания 1–3.')
    def eligible(w):
        if mode == 'gap':
            return w['kind'] == 'text_lab_gap'
        if mode in {'lex', 'truth'}:
            return w['kind'] == 'text_lab_bool' and w['task_number'] == (2 if mode == 'lex' else 3)
        return w['kind'] == 'text_lab_multi' and w['task_number'] == 3
    return [w for w in WORDS if eligible(w) and (not selected or w['rule_id'] in selected)]


def select_questions(user, config, *, teacher=False):
    mode = str(config.get('mode') or 'gap')
    if mode not in MODES:
        raise ValueError('Неизвестный режим тренажёра 1–3.')
    count = max(1, min(int(config.get('count') or 10), 60 if teacher else 30))
    if mode.startswith('task_exam_'):
        number = int(mode[-1])
        pool = [w for w in WORDS if w['task_number']==number and w['kind']==('text_lab_gap' if number==1 else 'text_lab_multi')]
        return [word_question(w) for w in random.sample(pool,min(count,len(pool)))]
    if mode == 'exam':
        if config.get('include_errors'):
            raise ValueError('Для формата 1–3 копилка выбирается отдельным режимом.')
        entries = [e for e in ENTRIES if all(e['tasks'][str(n)]['id'] in WORD_BY_ID for n in (1, 2, 3))]
        # Three separate tasks per common text: statistics and frozen checks count each once.
        return [word_question(WORD_BY_ID[e['tasks'][str(n)]['id']])
                for e in random.sample(entries, min(count, len(entries))) for n in (1, 2, 3)]
    pool = mode_pool(mode, config) if mode != 'errors' else []
    errors = []
    if mode == 'errors' or config.get('include_errors'):
        if teacher:
            if user.get('role') != 'teacher':
                raise PermissionError('Функция доступна только учителю.')
            with db() as con:
                rows = con.execute('''SELECT DISTINCT wp.word_id FROM word_progress wp JOIN users u ON u.user_id=wp.user_id
                    WHERE u.teacher_id=? AND u.role='student' AND wp.scope_id=? AND wp.due_reviews>0''',
                                   (user['user_id'], scope_id_for('errors'))).fetchall()
            errors = [WORD_BY_ID[r['word_id']] for r in rows if r['word_id'] in WORD_BY_ID]
        else:
            errors = error_bank_words(user['user_id'])
        if mode != 'errors':
            ids = {w['id'] for w in pool}
            errors = [w for w in errors if w['id'] in ids]
    if mode == 'errors':
        pool = errors
    if not pool:
        raise ValueError('В копилке пока нет подходящих ошибок.' if mode == 'errors' else 'Нет заданий по выбранной теме.')
    random.shuffle(errors)
    rest = [w for w in pool if w not in errors]
    if not teacher and mode != 'errors':
        # Prefer unseen questions; never mix progress from other trainers or modes.
        with db() as con:
            seen = {r[0] for r in con.execute('SELECT word_id FROM word_progress WHERE user_id=? AND scope_id=? AND cycle_seen=1',
                                            (user['user_id'], scope_id_for(mode, rule_ids=config.get('rule_ids'))))}
        fresh, old = [w for w in rest if w['id'] not in seen], [w for w in rest if w['id'] in seen]
        random.shuffle(fresh)
        random.shuffle(old)
        rest = fresh + old
    else:
        random.shuffle(rest)
    return [word_question(w) for w in (errors + rest)[:count]]


def start_practice(user, payload):
    mode = str(payload.get('mode') or 'gap')
    if payload.get('include_errors') and user.get('role') != 'teacher':
        raise PermissionError('Ошибки класса доступны только учителю.')
    questions = select_questions(user, payload)
    private = {}
    for q in questions:
        item = dict(q)
        item['correct_answer'] = item.pop('_correct_answer')
        private[item['question_id']] = item
    sid = secrets.token_hex(12)
    with SESSION_LOCK:
        # Retain completed results for retry-safe POSTs, but bound their lifetime and memory.
        expired = [key for key, value in PRACTICE_SESSIONS.items() if time.time() - value.get('created_at', 0) > 86400]
        for key in expired:
            PRACTICE_SESSIONS.pop(key, None)
        while len(PRACTICE_SESSIONS) >= 500:
            PRACTICE_SESSIONS.pop(next(iter(PRACTICE_SESSIONS)))
        PRACTICE_SESSIONS[sid] = {'user_id': user['user_id'], 'mode': mode,
                                'scope_id': scope_id_for(mode, rule_ids=payload.get('rule_ids')), 'questions': private,
                                'results': {}, 'completed': False, 'created_at': time.time()}
    return {'session_id': sid, 'mode': mode, 'questions': [public_question(q) for q in private.values()]}


def normalize_text(value):
    return re.sub(r'\s+', ' ', str(value).strip()).lower().replace('е\u0308', 'ё')


def answer_complete(question, raw):
    if question['kind'] == 'text_lab_bool':
        return isinstance(raw, str) and raw in {'true', 'false'}
    if question['kind'] == 'text_lab_multi':
        return isinstance(raw, str) and bool(re.fullmatch('[1-5]+', raw))
    return isinstance(raw, str) and bool(raw.strip())


def grade(question, raw):
    correct = question['correct_answer']
    if question['kind'] == 'text_lab_gap':
        return normalize_text(raw) in {normalize_text(a) for a in correct}, raw.strip(), '; '.join(correct)
    if question['kind'] == 'text_lab_multi':
        given = ''.join(sorted(set(raw)))
        return given == ''.join(sorted(set(correct))), given, correct
    return raw == correct, 'Верно' if raw == 'true' else 'Неверно', 'Верно' if correct == 'true' else 'Неверно'


def update_progress(con, user_id, scope, word_id, correct):
    row = con.execute('SELECT due_reviews,correct_count,error_count FROM word_progress WHERE user_id=? AND scope_id=? AND word_id=?',
                      (user_id, scope, word_id)).fetchone()
    due, good, bad = tuple(row) if row else (0, 0, 0)
    due = max(0, due - 1) if correct else REPEAT_ON_ERROR
    con.execute('''INSERT INTO word_progress(user_id,scope_id,word_id,cycle_seen,due_reviews,correct_count,error_count,last_seen_at)
        VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(user_id,scope_id,word_id) DO UPDATE SET cycle_seen=excluded.cycle_seen,
        due_reviews=excluded.due_reviews,correct_count=excluded.correct_count,error_count=excluded.error_count,last_seen_at=excluded.last_seen_at''',
                (user_id, scope, word_id, int(correct), due, good + int(correct), bad + int(not correct), now_iso()))


def record_attempt(con, user_id, session, question_id, question, raw, elapsed=None):
    if not answer_complete(question, raw):
        raise ValueError('Введите ответ или выберите варианты перед проверкой.')
    ok, given, correct = grade(question, raw)
    wid = question['source_word_id']
    for scope in {session['scope_id'], scope_id_for('errors')}:
        update_progress(con, user_id, scope, wid, ok)
    con.execute('''INSERT INTO attempts(attempt_id,user_id,mode,scope_id,word_id,rule_id,category,rule_name,
        question_id,prompt,given_answer,correct_answer,is_correct,created_at,time_spent_sec) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (secrets.token_hex(12), user_id, session['mode'], session['scope_id'], wid, question['rule_id'],
                 question['category'], question['rule_name'], question_id, describe_question(question), given, correct, int(ok), now_iso(), elapsed))
    return {'question_id': question_id, 'is_correct': ok, 'given_answer': given, 'correct_answer': correct,
            'explanation': question['explanation']}


def owned_session(user, payload):
    session = PRACTICE_SESSIONS.get(str(payload.get('session_id') or ''))
    if not session or session['user_id'] != user['user_id']:
        raise ValueError('Сессия тренировки не найдена.')
    return session


def _check_practice_answer(user, payload):
    session = owned_session(user, payload)
    if session['mode'] == 'exam':
        raise ValueError('В формате ЕГЭ проверяются все задания после завершения.')
    qid = str(payload.get('question_id') or '')
    if qid not in session['questions']:
        raise ValueError('Вопрос не найден в этой тренировке.')
    with db() as con:
        # Serialize duplicate checks before reading the session's result cache.
        con.execute('BEGIN IMMEDIATE')
        if qid in session['results']:
            return session['results'][qid]
        result = record_attempt(con, user['user_id'], session, qid, session['questions'][qid], payload.get('answer'), payload.get('time_spent_sec'))
    session['results'][qid] = result
    return result


def _submit_practice(user, payload):
    session = owned_session(user, payload)
    answers = payload.get('answers') or {}
    if not isinstance(answers, dict):
        raise ValueError('Некорректные ответы.')
    with db() as con:
        con.execute('BEGIN IMMEDIATE')
        pending = {qid: q for qid, q in session['questions'].items() if qid not in session['results']}
        if any(not answer_complete(q, answers.get(qid)) for qid, q in pending.items()):
            raise ValueError('Ответьте на все задания перед проверкой.')
        results = {qid: record_attempt(con, user['user_id'], session, qid, q, answers[qid], payload.get('time_spent_sec')) for qid, q in pending.items()}
    session['results'].update(results)
    session['completed'] = True
    rows = [session['results'][qid] for qid in session['questions']]
    return {'results': rows, 'correct': sum(r['is_correct'] for r in rows), 'total': len(rows)}


def check_practice_answer(user, payload):
    with SESSION_LOCK:
        return _check_practice_answer(user, payload)


def submit_practice(user, payload):
    with SESSION_LOCK:
        return _submit_practice(user, payload)


def build_test_file(user, payload):
    if user.get('role') != 'teacher':
        raise PermissionError('Функция доступна только учителю.')
    questions = select_questions(user, payload, teacher=True)
    lines, answers = ['ЕГЭ. Задания 1–3 · Лаборатория текста', ''], ['', 'Ответы', '']
    for i, question in enumerate(questions, 1):
        printable = dict(question)
        if question['highlight_ranges']:
            text, end, marked = question['text'], 0, ''
            for a, b in sorted(question['highlight_ranges']):
                if a < end:
                    continue
                marked += text[end:a] + '⟦' + text[a:b] + '⟧'
                end = b
            printable['text'] = marked + text[end:]
        lines += [f'{i}. ' + describe_question(printable), '']
        private = {**question, 'correct_answer': question['_correct_answer']}
        key = private['correct_answer']
        key = '; '.join(key) if isinstance(key, list) else {'true': 'Верно', 'false': 'Неверно'}.get(key, key)
        answers.append(f'{i}. {key}')
    return ('\n'.join(lines + [SOURCE_LABEL] + answers) + '\n').encode(), 'ege1-3-test.txt', 'text/plain; charset=utf-8'
