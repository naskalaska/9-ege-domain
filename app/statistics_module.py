"""Cross-activity reporting with ownership checks and an unabridged paged journal."""
from contextlib import closing
from datetime import date
import csv
import io
import json
import math
import re
from attempt_content import describe_question

TASKS = {f'ege{n}':f'Задание {n}' for n in (5,9,10,11,12,13,14,15)}


def diagnostic(mode, question_id):
    return int(any(str(mode).endswith(s) for s in (':line_word',':exam_word',':sentence_word'))
               or bool(re.search(r':row\d+:', str(question_id))))


def configure(s, con):
    words, rules = {}, {}
    for activity in TASKS:
        module = s if activity == 'ege9' else getattr(s,activity+'_module')
        for word_id in getattr(module,'WORD_BY_ID',getattr(module,'GROUP_BY_ID',{})):
            words[word_id] = activity
        for rule in module.RULES:
            rules[rule['rule_id']] = activity

    def activity(scope, word_id, rule_id, mode):
        scope = str(scope or '')
        game_scope = scope if scope.startswith('game:') else str(rule_id or '')
        if game_scope.startswith('game:'):
            slug = game_scope.split(':')[1]
            slug = {'berry-season':'berry-season-ik-ek','butterflies':'butterflies-participle-suffixes'}.get(slug,slug)
            return 'game:'+slug
        if mode == 'game':
            return 'game:unknown'
        for key in TASKS:
            if scope.startswith(key+':'):
                return key
        return words.get(word_id) or rules.get(rule_id) or ('ege5' if str(mode).startswith('paronym') else 'ege9')
    con.create_function('stats_activity',4,activity,deterministic=True)
    con.create_function('stats_detail',2,diagnostic,deterministic=True)
    con.create_function('stats_contains',2,lambda text,query:int(str(query).casefold() in str(text or '').casefold()),deterministic=True)


def authorized_students(con, user, student_id=''):
    if user['role'] == 'teacher':
        students = [dict(r) for r in con.execute("SELECT user_id,display_name FROM users WHERE teacher_id=? AND role='student' ORDER BY display_name,user_id",(user['user_id'],))]
        if student_id and student_id not in {r['user_id'] for r in students}:
            raise PermissionError('Можно просматривать только своих учеников.')
        return [r for r in students if not student_id or r['user_id'] == student_id]
    if user['role'] != 'student':
        raise PermissionError('Статистика доступна ученикам и учителям.')
    if student_id and student_id != user['user_id']:
        raise PermissionError('Можно просматривать только свою статистику.')
    return [{'user_id':user['user_id'],'display_name':user['display_name']}]


def source(con, user, params):
    student_id = str(params.get('student_id') or '')
    students = authorized_students(con,user,student_id)
    if user['role'] == 'teacher' and not student_id:
        where = "u.teacher_id=? AND u.role='student'"
        args = [user['user_id']]
    else:
        where = 'a.user_id=?'
        args = [student_id or user['user_id']]
    try:
        offset = int(params.get('offset_minutes') or 0)
    except (ValueError,TypeError):
        raise ValueError('Некорректный часовой пояс.') from None
    if not -840 <= offset <= 840:
        raise ValueError('Некорректный часовой пояс.')
    for key,operator in [('from','>='),('to','<=')]:
        value = str(params.get(key) or '')
        if value:
            try:
                date.fromisoformat(value)
            except ValueError:
                raise ValueError('Дата должна быть в формате ГГГГ-ММ-ДД.') from None
            where += f' AND date(a.created_at,?){operator}?'
            args.extend([f'{offset} minutes',value])
    if params.get('from') and params.get('to') and params['from'] > params['to']:
        raise ValueError('Начало периода позже окончания.')
    query = f'''WITH records AS (
      SELECT a.*,u.display_name,stats_activity(a.scope_id,a.word_id,a.rule_id,a.mode) activity,
      stats_detail(a.mode,a.question_id) is_detail
      FROM attempts a JOIN users u ON u.user_id=a.user_id WHERE {where})'''
    return query,args,students


def title(s, activity):
    extra = {'game:fluffs':'Пушинки — свои наборы','game:unknown':'Игры — прежние записи'}
    return TASKS.get(activity) or extra.get(activity) or s.HTML_GAME_TITLES.get(activity.removeprefix('game:'),
        'Игра: '+activity.removeprefix('game:'))


def metrics(row):
    row = dict(row)
    row['total'] = int(row.get('total') or 0)
    row['correct'] = int(row.get('correct') or 0)
    row['errors'] = row['total']-row['correct']
    row['accuracy'] = round(100*row['correct']/row['total'],1) if row['total'] else None
    return row


def overview(s, user, params=None):
    params = params or {}
    with closing(s.db()) as con:
        configure(s,con)
        query,args,students = source(con,user,params)
        summary = metrics(con.execute(query+''' SELECT COUNT(*) total,SUM(is_correct) correct,
            MAX(created_at) last_active FROM records WHERE is_detail=0''',args).fetchone())
        rows = con.execute(query+''' SELECT activity,COUNT(*) total,SUM(is_correct) correct,
            MAX(created_at) last_active FROM records WHERE is_detail=0 GROUP BY activity''',args).fetchall()
        by_activity = {r['activity']:metrics(r) for r in rows}
        for key in TASKS:
            by_activity.setdefault(key,metrics({'activity':key}))
        for key,item in by_activity.items():
            item['title'] = title(s,key)
        rows = con.execute(query+''' SELECT user_id,COUNT(*) total,SUM(is_correct) correct,
            MAX(created_at) last_active FROM records WHERE is_detail=0 GROUP BY user_id''',args).fetchall()
        by_user = {r['user_id']:metrics(r) for r in rows}
        for student in students:
            student.update(by_user.get(student['user_id'],metrics({})))
        topics = [metrics(r) for r in con.execute(query+''' SELECT activity,category,rule_name,
            COUNT(*) total,SUM(is_correct) correct FROM records WHERE is_detail=0
            GROUP BY activity,category,rule_name''',args)]
        for item in topics:
            item['activity_title'] = title(s,item['activity'])
        strengths = sorted([r for r in topics if r['total']>=5 and r['accuracy']>=80],
            key=lambda r:(-r['accuracy'],-r['total']))[:5]
        attention = sorted([r for r in topics if r['errors']],key=lambda r:(-r['errors'],r['accuracy']))[:5]
        ordered = [by_activity[key] for key in TASKS]+sorted(
            [item for key,item in by_activity.items() if key not in TASKS],key=lambda r:r['title'])
        return {'summary':summary,'by_activity':ordered,'students':students,
                'strengths':strengths,'attention':attention,'role':user['role']}


def history_query(s, con, user, params):
    configure(s,con)
    query,args,_ = source(con,user,params)
    filters = []
    activity = str(params.get('activity') or '')
    if activity:
        if activity not in TASKS and not activity.startswith('game:') and activity != 'games':
            raise ValueError('Неизвестное задание.')
        filters.append("activity LIKE 'game:%'" if activity == 'games' else 'activity=?')
        if activity != 'games':
            args.append(activity)
    status = str(params.get('status') or 'all')
    if status not in {'all','correct','incorrect'}:
        raise ValueError('Неизвестный фильтр ответов.')
    if status != 'all':
        filters.append('is_correct=?');args.append(int(status=='correct'))
    kind = str(params.get('kind') or 'all')
    if kind not in {'all','answers','details'}:
        raise ValueError('Неизвестный тип записи.')
    if kind != 'all':
        filters.append('is_detail=?');args.append(int(kind=='details'))
    search = str(params.get('search') or '').strip()[:200]
    if search:
        filters.append("stats_contains(COALESCE(prompt,'')||' '||COALESCE(given_answer,'')||' '||COALESCE(correct_answer,'')||' '||COALESCE(rule_name,''),?)")
        args.append(search)
    query += ' SELECT * FROM records'+(' WHERE '+' AND '.join(filters) if filters else '')
    return query,args


def enrich(s, rows, con=None):
    rows = [dict(row) for row in rows]
    contents = {}
    letter_checks = {}
    # Diagnostic records can share the exercise ID (tasks 10–12), or append
    # a row/word suffix (task 9). Resolve within the same pupil only, including
    # when filters or pagination have excluded the exercise's own record.
    def exercise_key(row):
        return row['user_id'], re.split(r':row\d+:', str(row['question_id']), maxsplit=1)[0]

    detail_keys = {exercise_key(row) for row in rows if row['is_detail']}
    parents = {}
    if con is not None and detail_keys:
        students = list({key[0] for key in detail_keys})
        questions = list({key[1] for key in detail_keys})
        candidates = con.execute(f'''SELECT * FROM attempts
            WHERE user_id IN ({','.join('?' for _ in students)})
              AND question_id IN ({','.join('?' for _ in questions)})
            ORDER BY created_at DESC,attempt_id DESC''', [*students,*questions])
        for candidate in candidates:
            key = (candidate['user_id'],candidate['question_id'])
            if key in detail_keys and not diagnostic(candidate['mode'],candidate['question_id']):
                parents.setdefault(key,dict(candidate))
    unresolved = {(row['user_id'],row['question_id']) for row in rows
                  if not row['is_detail'] and not row['activity'].startswith('game:')}
    unresolved |= detail_keys
    if con is not None and unresolved:
        students = list({key[0] for key in unresolved})
        placeholders = ','.join('?' for _ in students)
        assignments = con.execute(f'''SELECT a.student_id,t.questions_json FROM assigned_tests t
            JOIN assigned_test_students a ON a.test_id=t.id WHERE a.student_id IN ({placeholders})''',students)
        for assignment in assignments:
            for snap in json.loads(assignment['questions_json']):
                key = (assignment['student_id'],snap['question_id'])
                if key in unresolved:
                    contents[key] = snap
        checks = con.execute(f'''SELECT student_id,question_id,result_json FROM assigned_test_checks
            WHERE student_id IN ({placeholders})''',students)
        for check in checks:
            key = (check['student_id'],check['question_id'])
            if key in unresolved:
                result = json.loads(check['result_json'])
                if result.get('letter_results'):
                    letter_checks[key] = result['letter_results']
    result = []
    for row in rows:
        item = dict(row)
        activity = item['activity']
        item['activity_title'] = title(s,activity)
        module = s if activity == 'ege9' else getattr(s,activity+'_module',None)
        word = getattr(module,'WORD_BY_ID',{}).get(item.get('word_id')) if module else None
        if word:
            item['explanation'] = word.get('explanation') or ''
            item['correct_spelling'] = word.get('correct_spelling') or ''
        snapshot = contents.get((item['user_id'],item['question_id'])) if not item['is_detail'] else None
        if snapshot:
            item['prompt'] = describe_question(snapshot['public'])
            item['explanation'] = snapshot['question'].get('explanation') or ''
            item['correct_spelling'] = snapshot['question'].get('correct_spelling') or ''
        if not item['is_detail']:
            item['letter_results'] = letter_checks.get((item['user_id'],item['question_id']),[])
        # Row-selection diagnostics inherit the whole exercise answer. They
        # are not evidence that the pupil entered that answer for this word.
        given = str(item.get('given_answer') or '')
        row_detail = item['is_detail'] and (
            bool(re.fullmatch(r'[1-5]+|—', given))
            or bool(re.search(r':row\d+:', str(item.get('question_id')))))
        if row_detail:
            # Never replace a word's prompt with the five-row exercise.
            if word:
                item['prompt'] = word.get('variant') or item['prompt']
            item['detail_kind'] = 'row_selection'
            item['answer_label'] = 'Ответ на задание'
            item['correct_answer_label'] = 'Эталон слова'
            item['answer_note'] = ('Слово из строки, выбор которой отмечен в этой записи. '
                                   'Отдельный ответ на слово не вводился.')
            item['given_answer'] = ('Выбор строки: ' + given if given.startswith('строка ')
                                    else 'Выбранные строки: ' + (given or '—'))
            item['correct_answer'] = 'Эталон слова: ' + str(item.get('correct_answer') or '—')
            parent = parents.get(exercise_key(item))
            snap = contents.get(exercise_key(item))
            key = (parent or {}).get('correct_answer') or (snap or {}).get('question',{}).get('correct_answer')
            answer = (parent or {}).get('given_answer')
            if answer is None and re.fullmatch(r'[1-5]*|—', given):
                answer = given
            if key is not None and re.fullmatch(r'[1-5]+', str(key)) and answer is not None:
                item['exercise_given_answer'] = str(answer) or '—'
                item['exercise_correct_answer'] = str(key)
                item['word_correct_answer'] = str(row.get('correct_answer') or '—')
                item['answer_note'] = ('Ответ на всё задание указан номерами строк. '
                                       'Ниже — эталон буквы для этого слова; отдельный ответ на слово не вводился.')
        item['content_available'] = bool(item.get('given_answer') and item.get('correct_answer'))
        from student_workspace import repeat_kind
        item['can_repeat'] = not item['is_correct'] and bool(repeat_kind(s,row,snapshot))
        if item['activity'].startswith('game:'):
            slug = item['activity'].split(':',1)[1]
            if slug in s.HTML_GAMES or slug in s.PUBLIC_GAMES:
                item['repeat_game_url'] = '/games/'+slug+'/index.html'
        result.append(item)
    return result


def history(s, user, params=None):
    params = params or {}
    try:
        page = max(1,int(params.get('page') or 1))
        size = max(1,min(100,int(params.get('page_size') or 30)))
    except (ValueError,TypeError):
        raise ValueError('Неверный номер страницы.') from None
    with closing(s.db()) as con:
        query,args = history_query(s,con,user,params)
        total = con.execute('SELECT COUNT(*) FROM ('+query+')',args).fetchone()[0]
        pages = max(1,math.ceil(total/size));page = min(page,pages)
        rows = con.execute(query+' ORDER BY created_at DESC,attempt_id DESC LIMIT ? OFFSET ?',
            [*args,size,(page-1)*size]).fetchall()
        return {'items':enrich(s,rows,con),'total':total,'page':page,'pages':pages,'page_size':size}


def export(s, user, params=None):
    with closing(s.db()) as con:
        query,args = history_query(s,con,user,params or {})
        rows = enrich(s,con.execute(query+' ORDER BY created_at DESC,attempt_id DESC',args).fetchall(),con)
        out = io.StringIO(newline='');writer = csv.writer(out,delimiter=';')
        writer.writerow(['Дата','Ученик','Задание / игра','Тема','Текст задания','Ответ ученика','Правильный ответ','Верно','Тип записи','Эталон буквы в слове','Проверка вставленных букв'])
        for row in rows:
            values = [row['created_at'],row['display_name'],title(s,row['activity']),row['rule_name'],row['prompt'],
                      row.get('exercise_given_answer',row['given_answer']),
                      row.get('exercise_correct_answer',row['correct_answer']),'да' if row['is_correct'] else 'нет',
                      'Подробность по слову' if row['is_detail'] else 'Ответ на задание',row.get('word_correct_answer',''),
                      '; '.join(f"{r['prompt']}: {r['given_answer']} → {r['correct_answer']}" for r in row.get('letter_results',[]))]
            # Keep user-generated text as text when opened in spreadsheet programs.
            writer.writerow(["'"+str(v) if str(v or '').startswith(('=','+','-','@')) else v for v in values])
        return out.getvalue().encode('utf-8-sig'),'statistics.csv','text/csv; charset=utf-8'
