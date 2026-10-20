"""A pupil's workspace, deadline calendar, and persistent practice from errors."""
import copy
import json
import re
import secrets
from datetime import datetime, timedelta, timezone
from contextlib import closing
import learning_module as learning
import statistics_module as statistics


def student_for(con,user,student_id=''):
    students = statistics.authorized_students(con,user,str(student_id or ''))
    if user['role'] == 'teacher' and not student_id:
        raise ValueError('Выберите ученика.')
    return students[0]


def assignments_for(s,user,student_id=''):
    data = learning.overview(s,user)
    if user['role'] == 'student':
        return data['tests']
    result = []
    for test in data['tests']:
        for pupil in test['students']:
            if not student_id or pupil['student_id'] == student_id:
                result.append({**{k:v for k,v in test.items() if k != 'students'},**pupil})
    return result


def profile(s,user,params):
    with closing(s.db()) as con:
        pupil = student_for(con,user,params.get('student_id'))
        sid = pupil['user_id']
        groups = [dict(r) for r in con.execute('''SELECT g.id,g.title FROM student_groups g
            JOIN student_group_members m ON m.group_id=g.id JOIN users u ON u.user_id=m.student_id
            WHERE m.student_id=? AND g.teacher_id=u.teacher_id ORDER BY g.title''',(sid,))]
        filters = {'student_id':sid,'offset_minutes':params.get('offset_minutes') or 0}
        statistics.configure(s,con)
        query,args,_ = statistics.source(con,user,filters)
        offset = int(filters['offset_minutes'])
        today = (datetime.now(timezone.utc)+timedelta(minutes=offset)).date()
        monday = today-timedelta(days=today.weekday(),weeks=7)
        daily = [dict(r) for r in con.execute(query+''' SELECT date(created_at,?) day,
            COUNT(*) total,SUM(is_correct) correct FROM records WHERE is_detail=0
            AND date(created_at,?)>=? GROUP BY day''',
            [*args,f'{offset} minutes',f'{offset} minutes',monday.isoformat()])]
    trend=[]
    for index in range(8):
        start = monday+timedelta(weeks=index)
        days = [r for r in daily if start.isoformat()<=r['day']<(start+timedelta(days=7)).isoformat()]
        trend.append(statistics.metrics({'week':start.isoformat(),'total':sum(r['total'] for r in days),
                                         'correct':sum(r['correct'] for r in days)}))
    tests = assignments_for(s,user,sid)
    return {'student':pupil,'groups':groups,'statistics':statistics.overview(s,user,filters),
            'assignments':tests,'trend':trend,
            'pending':sum(not t.get('completed_at') and not t.get('revoked_at') for t in tests),
            'overdue':sum(bool(t.get('overdue')) for t in tests)}


def calendar(s,user,params):
    sid = str(params.get('student_id') or '')
    with closing(s.db()) as con:
        students = statistics.authorized_students(con,user,sid)
    tests = assignments_for(s,user,sid)
    return {'items':tests,'role':user['role'],'students':students}


def repeat_kind(s,item,snapshot=None):
    """Offer only exercises we can actually recover, never guess a lost key."""
    activity = item['activity']
    if activity in statistics.TASKS:
        module = learning.module_for(s,activity)
        if activity=='ege5' and any(item.get('prompt') in {r['sentence'],module.sentence_with_blank(r)}
                                   for r in module.ROWS_BY_GROUP.get(item.get('word_id'),[])):
            return 'paronym_word'
        if item.get('word_id') in getattr(module,'WORD_BY_ID',{}):
            return 'word'
    if snapshot and not item['is_detail']:
        return 'snapshot'
    prompt,key = str(item.get('prompt') or ''),str(item.get('correct_answer') or '')
    if not item['is_detail'] and prompt and key and key != '—':
        if re.fullmatch(r'[1-5]+',key) and re.search(r'(?m)^5\)',prompt):
            return 'rows'
        if re.fullmatch(r'[1-5]\|[^|]+',key) and re.search(r'(?m)^5\)',prompt):
            return 'paronym'
        if activity.startswith('game:') and len(key)<=80 and re.search(r'\.{2,}|…',prompt) and not key.startswith(('[','{')):
            return 'text'
    return None


def repeat_error(s,user,payload):
    attempt_id = str(payload.get('attempt_id') or '')
    due = learning.parse_due(payload.get('due_at'))
    if user['role'] != 'teacher' and due:
        raise PermissionError('Срок повторения назначает учитель.')
    with learning.connection(s) as con:
        con.execute('BEGIN IMMEDIATE')
        statistics.configure(s,con)
        if not attempt_id and payload.get('question_id') and user['role']=='student':
            found = con.execute('''SELECT attempt_id FROM attempts WHERE user_id=? AND question_id=?
                AND is_correct=0 AND stats_detail(mode,question_id)=0 ORDER BY created_at DESC LIMIT 1''',
                (user['user_id'],str(payload['question_id']))).fetchone()
            attempt_id = found[0] if found else ''
        attempt = con.execute('''SELECT *,stats_activity(scope_id,word_id,rule_id,mode) activity,
            stats_detail(mode,question_id) is_detail FROM attempts WHERE attempt_id=?''',(attempt_id,)).fetchone()
        if not attempt:
            raise ValueError('Решение не найдено.')
        item = dict(attempt)
        student_for(con,user,item['user_id'])
        if item['is_correct']:
            raise ValueError('Для повторения выберите ошибочный ответ.')
        existing = con.execute('''SELECT r.test_id FROM error_repetitions r
            JOIN assigned_test_students a ON a.test_id=r.test_id AND a.student_id=r.student_id
            WHERE r.attempt_id=? AND r.student_id=? AND a.completed_at IS NULL AND a.revoked_at IS NULL
            ORDER BY a.started_at DESC LIMIT 1''',(attempt_id,item['user_id'])).fetchone()
        if existing:
            return {'id':existing['test_id'],'existing':True}
        original_id = re.split(r':row\d+:',str(item['question_id']),maxsplit=1)[0]
        frozen = None
        for assignment in con.execute('''SELECT t.questions_json FROM assigned_tests t
            JOIN assigned_test_students a ON a.test_id=t.id WHERE a.student_id=?''',(item['user_id'],)):
            frozen = next((q for q in json.loads(assignment[0]) if q['question_id']==original_id),None)
            if frozen:
                break
        kind = repeat_kind(s,item,frozen)
        if not kind:
            raise ValueError('Недостаточно сохранённых данных для точного повторения. Откройте соответствующий тренажёр или игру.')
        activity = item['activity']
        if kind == 'snapshot':
            snap = copy.deepcopy(frozen)
        elif kind == 'paronym_word':
            module = s.ege5_module
            source = next(r for r in module.ROWS_BY_GROUP[item['word_id']]
                          if item['prompt'] in {r['sentence'],module.sentence_with_blank(r)})
            maker = module.make_tf_question if str(item['mode']).startswith('paronym_tf') else module.make_choice_question
            snap = learning.snapshot_question(module,activity,'review',maker(source))
        elif kind == 'word':
            module = learning.module_for(s,activity)
            maker = module.make_word_question if activity in {'ege9','ege10','ege11','ege12'} else module.word_question
            snap = learning.snapshot_question(module,activity,'review',maker(module.WORD_BY_ID[item['word_id']]))
        else:
            q = {'question_id':'','kind':'error_review','prompt':item['prompt'],'review_type':kind,
                 'rule_id':item['rule_id'],'rule_name':item['rule_name'],'category':item['category'],
                 'correct_answer':item['correct_answer']}
            snap = {'activity':activity,'mode':'review','scope_id':activity+':review',
                    'question':q,'public':{k:v for k,v in q.items() if k!='correct_answer'}}
        qid = secrets.token_hex(12)
        snap['question_id'] = qid
        snap['question']['question_id'] = qid
        snap['public']['question_id'] = qid
        snap['scope_id'] = activity+':review'
        test_id = secrets.token_hex(12)
        teacher_id = con.execute('SELECT teacher_id FROM users WHERE user_id=?',(item['user_id'],)).fetchone()[0]
        teacher_id = teacher_id or item['user_id']
        con.execute('INSERT INTO assigned_tests VALUES(?,?,?,?,?)',
            (test_id,teacher_id,'Повторение ошибки · '+statistics.title(s,activity),json.dumps([snap],ensure_ascii=False),s.now_iso()))
        con.execute('INSERT INTO assigned_test_students(test_id,student_id,due_at) VALUES(?,?,?)',
                    (test_id,item['user_id'],due))
        con.execute('INSERT INTO error_repetitions VALUES(?,?,?,?)',(test_id,item['user_id'],attempt_id,user['user_id']))
    return {'id':test_id,'existing':False}


def record_review(s,con,user,snap,answer,elapsed):
    q = snap['question']
    def normalize(value):
        return re.sub(r'\s+','',str(value or '')).lower().replace('ё','ё')
    if q['review_type']=='paronym':
        answer = f"{answer.get('row','')}|{answer.get('word','')}" if isinstance(answer,dict) else ''
    given = str(answer or '').strip()
    if q['review_type']=='rows':
        given = ''.join(sorted(set(re.findall('[1-5]',given))))
    correct = normalize(given)==normalize(q['correct_answer'])
    con.execute('''INSERT INTO attempts (attempt_id,user_id,mode,scope_id,rule_id,category,rule_name,
        question_id,prompt,given_answer,correct_answer,is_correct,created_at,time_spent_sec)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(secrets.token_hex(12),user['user_id'],'review',snap['scope_id'],
        q.get('rule_id'),q.get('category'),q.get('rule_name'),snap['question_id'],q['prompt'],given,
        q['correct_answer'],int(correct),s.now_iso(),elapsed))
    return {'question_id':snap['question_id'],'given_answer':given,'correct_answer':q['correct_answer'],
            'is_correct':correct,'explanation':q.get('explanation',''),'correct_spelling':q.get('correct_spelling','')}
