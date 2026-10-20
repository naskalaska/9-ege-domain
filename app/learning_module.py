"""Persistent teacher assignments and authenticated game results."""
import json
import secrets
import random
from datetime import datetime, timezone
from contextlib import contextmanager, closing
from attempt_content import describe_question


class RevokedTestError(PermissionError):
    code = 'assignment_revoked'


@contextmanager
def connection(s):
    with closing(s.db()) as con:
        with con:
            yield con


def ensure_schema(con):
    con.executescript("""
    CREATE TABLE IF NOT EXISTS student_groups (
      id TEXT PRIMARY KEY, teacher_id TEXT NOT NULL, title TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS student_group_members (
      group_id TEXT NOT NULL, student_id TEXT NOT NULL, PRIMARY KEY(group_id, student_id));
    CREATE TABLE IF NOT EXISTS assigned_tests (
      id TEXT PRIMARY KEY, teacher_id TEXT NOT NULL, title TEXT NOT NULL,
      questions_json TEXT NOT NULL, created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS assigned_test_students (
      test_id TEXT NOT NULL, student_id TEXT NOT NULL, seen_at TEXT, started_at TEXT,
      completed_at TEXT, answers_json TEXT, result_json TEXT, PRIMARY KEY(test_id, student_id));
    CREATE TABLE IF NOT EXISTS game_results (
      user_id TEXT NOT NULL, event_id TEXT NOT NULL, slug TEXT NOT NULL,
      public_id TEXT, created_at TEXT NOT NULL, PRIMARY KEY(user_id, event_id));
    CREATE INDEX IF NOT EXISTS idx_assigned_student ON assigned_test_students(student_id, completed_at);
    CREATE INDEX IF NOT EXISTS idx_assigned_teacher ON assigned_tests(teacher_id, created_at);
    CREATE TABLE IF NOT EXISTS assigned_test_checks (
      test_id TEXT NOT NULL, student_id TEXT NOT NULL, question_id TEXT NOT NULL,
      answer_json TEXT NOT NULL, result_json TEXT NOT NULL, checked_at TEXT NOT NULL,
      PRIMARY KEY(test_id, student_id, question_id));
    """)
    columns = {r[1] for r in con.execute('PRAGMA table_info(assigned_test_students)')}
    if 'revoked_at' not in columns:
        con.execute('ALTER TABLE assigned_test_students ADD COLUMN revoked_at TEXT')
    if 'due_at' not in columns:
        con.execute('ALTER TABLE assigned_test_students ADD COLUMN due_at TEXT')
    con.execute('''CREATE TABLE IF NOT EXISTS error_repetitions (
        test_id TEXT PRIMARY KEY, student_id TEXT NOT NULL, attempt_id TEXT NOT NULL, created_by TEXT NOT NULL)''')


def parse_due(value):
    if value in (None,''):
        return None
    try:
        due = datetime.fromisoformat(str(value).replace('Z','+00:00'))
        if due.tzinfo is None:
            raise ValueError()
        return due.astimezone(timezone.utc).isoformat()
    except (ValueError,TypeError,OverflowError):
        raise ValueError('Укажите корректный срок с часовым поясом.') from None


def deadline_status(item, now=None):
    now = now or datetime.now(timezone.utc)
    due = datetime.fromisoformat(item['due_at']) if item.get('due_at') else None
    item['overdue'] = bool(due and not item.get('completed_at') and not item.get('revoked_at') and due < now)
    item['submitted_late'] = bool(due and item.get('completed_at') and datetime.fromisoformat(item['completed_at']) > due)
    return item


def test_outline(snapshots):
    counts = {}
    for snap in snapshots:
        key = snap['activity']
        counts[key] = counts.get(key, 0) + 1
    return [{'activity':key, 'title':'Игра' if key.startswith('game:') else 'Задание ' + key.removeprefix('ege'), 'count':n}
            for key,n in counts.items()]


def checks_for(con, test_id, student_id):
    return {r['question_id']:json.loads(r['result_json']) for r in con.execute(
        'SELECT question_id,result_json FROM assigned_test_checks WHERE test_id=? AND student_id=?',
        (test_id,student_id))}


def module_for(s, activity):
    if activity == "ege9":
        return s
    if activity not in {"ege5", "ege10", "ege11", "ege12", "ege13", "ege14", "ege15"}:
        raise ValueError("Выберите учебное задание.")
    return getattr(s, activity + "_module")


def own_students(s, con, user, ids):
    s.require_teacher(user)
    if not isinstance(ids, list) or not ids:
        raise ValueError("Выберите учеников.")
    ids = list(dict.fromkeys(str(value) for value in ids))
    allowed = {r[0] for r in con.execute("SELECT user_id FROM users WHERE teacher_id=? AND role='student'", (user["user_id"],))}
    if not set(ids) <= allowed:
        raise PermissionError("Можно выбирать только своих учеников.")
    return ids


def overview(s, user):
    with connection(s) as con:
        if user["role"] == "teacher":
            students = [dict(r) for r in con.execute("SELECT user_id,display_name FROM users WHERE teacher_id=? AND role='student' ORDER BY display_name", (user["user_id"],))]
            groups = [dict(r) for r in con.execute("SELECT * FROM student_groups WHERE teacher_id=? ORDER BY title", (user["user_id"],))]
            for group in groups:
                group["student_ids"] = [r[0] for r in con.execute("SELECT student_id FROM student_group_members WHERE group_id=?", (group["id"],))]
            tests = [dict(r) for r in con.execute("SELECT id,title,created_at,questions_json FROM assigned_tests WHERE teacher_id=? ORDER BY created_at DESC", (user["user_id"],))]
            for test in tests:
                snapshots = json.loads(test.pop('questions_json'))
                test['total'] = len(snapshots)
                test['outline'] = test_outline(snapshots)
                test["students"] = [dict(r) for r in con.execute("""SELECT a.student_id,u.display_name,a.started_at,a.completed_at,a.result_json,a.revoked_at,a.due_at
                  FROM assigned_test_students a JOIN users u ON u.user_id=a.student_id WHERE a.test_id=?""", (test["id"],))]
                for student in test["students"]:
                    result = json.loads(student.pop("result_json") or "null")
                    student["result"] = result
                    checks = checks_for(con, test['id'], student['student_id'])
                    student['checked'] = result['total'] if result else len(checks)
                    student['correct'] = result['correct'] if result else sum(bool(r['is_correct']) for r in checks.values())
                    deadline_status(student)
            return {"students": students, "groups": groups, "tests": tests}
        tests = [dict(r) for r in con.execute("""SELECT t.id,t.title,t.created_at,
          CASE WHEN t.teacher_id=a.student_id THEN 'Самостоятельное повторение' ELSE u.display_name END AS teacher_name,
          a.seen_at,a.started_at,a.completed_at,a.result_json,a.revoked_at,a.due_at,t.questions_json FROM assigned_tests t
          JOIN assigned_test_students a ON a.test_id=t.id JOIN users u ON u.user_id=t.teacher_id
          WHERE a.student_id=? ORDER BY t.created_at DESC""", (user["user_id"],))]
        for test in tests:
            test["result"] = json.loads(test.pop("result_json") or "null")
            snapshots = json.loads(test.pop('questions_json'))
            test['total'] = len(snapshots)
            test['outline'] = test_outline(snapshots)
            test['checked'] = test['total'] if test['completed_at'] else len(checks_for(con,test['id'],user['user_id']))
            deadline_status(test)
        return {"tests": tests, "unread": sum(not t["revoked_at"] and not t["seen_at"] and not t["completed_at"] for t in tests),
                "pending": sum(not t["revoked_at"] and not t["completed_at"] for t in tests)}


def save_group(s, user, payload):
    with connection(s) as con:
        ids = own_students(s, con, user, payload.get("student_ids"))
        title = str(payload.get("title") or "").strip()[:120]
        if not title:
            raise ValueError("Введите название группы.")
        group_id = str(payload.get("id") or secrets.token_hex(12))
        existing = con.execute("SELECT teacher_id FROM student_groups WHERE id=?", (group_id,)).fetchone()
        if existing and existing[0] != user["user_id"]:
            raise PermissionError("Группа другого учителя.")
        con.execute("INSERT INTO student_groups VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET title=excluded.title", (group_id, user["user_id"], title))
        con.execute("DELETE FROM student_group_members WHERE group_id=?", (group_id,))
        con.executemany("INSERT INTO student_group_members VALUES(?,?)", [(group_id, i) for i in ids])
    return {"id": group_id}


def create_test(s, user, payload):
    s.require_teacher(user)
    due_at = parse_due(payload.get('due_at'))
    with connection(s) as con:
        ids = list(payload.get("student_ids") or [])
        if payload.get("all_students"):
            ids += [r[0] for r in con.execute("SELECT user_id FROM users WHERE teacher_id=? AND role='student'", (user["user_id"],))]
        for group_id in payload.get("group_ids") or []:
            group = con.execute("SELECT teacher_id FROM student_groups WHERE id=?", (str(group_id),)).fetchone()
            if not group or group[0] != user["user_id"]:
                raise PermissionError("Группа другого учителя.")
            ids += [r[0] for r in con.execute("SELECT student_id FROM student_group_members WHERE group_id=?", (group_id,))]
        ids = own_students(s, con, user, ids)
    title = str(payload.get("title") or "Назначенный тест").strip()[:160]
    config = payload.get("config") or {}
    require_letters = bool(config.get('require_letters'))
    activity = str(config.get("activity") or "ege9")
    specs = [(activity, config)]
    if activity == "orthography-ege":
        counts = s.ege_orthography_module.task_counts_from_payload(config)
        specs = [(a, {"mode": s.ege_orthography_module.TASKS[a]["mode"], "count": n}) for a, n in counts.items()]
    snapshots = []
    for activity, config in specs:
        module = module_for(s, activity)
        count = max(1, min(int(config.get("count") or 10), 60))
        if config.get("mode") == "errors" or (config.get("include_errors") and config.get("mode") not in {
            "paronym_exam", "line_ne", "line_spelling", "exam", "sentence_nn"
        }):
            snapshots.extend(class_error_variant(s, module, user, activity, config, count))
            continue
        while count:
            batch = min(count, 30)
            data = module.start_practice(user, {**config, "count": batch})
            session = module.PRACTICE_SESSIONS.pop(data["session_id"])
            public_by_id = {q["question_id"]: q for q in data["questions"]}
            for question_id, private in session["questions"].items():
                # Keep a frozen answer key on the server, never in the public payload.
                snapshots.append({"activity": activity, "mode": session["mode"], "scope_id": session["scope_id"],
                                  "question": private, "question_id": question_id,
                                  "public": {k: v for k, v in public_by_id[question_id].items()
                                             if k not in {"explanation", "correct_spelling"}}})
            count -= batch
    if not snapshots or len(snapshots) > 210:
        raise ValueError("В тесте должно быть от 1 до 210 вопросов.")
    for snap in snapshots:
        if snap['question']['kind'] == 'line':
            snap['question']['require_letters'] = require_letters
            snap['public']['require_letters'] = require_letters
    test_id = secrets.token_hex(12)
    with connection(s) as con:
        con.execute("INSERT INTO assigned_tests VALUES(?,?,?,?,?)", (test_id, user["user_id"], title, json.dumps(snapshots, ensure_ascii=False), s.now_iso()))
        con.executemany("INSERT INTO assigned_test_students(test_id,student_id,due_at) VALUES(?,?,?)", [(test_id, i,due_at) for i in ids])
    return {"id": test_id, "recipients": len(ids), "total": len(snapshots)}


def class_error_variant(s, module, user, activity, config, count):
    """Use pupils' error banks when composing a teacher's word test."""
    if activity == "ege5":
        _, words = s.ege5_test_rows_for_payload(user, config, count)
        make_question = module.make_choice_question
    elif activity in {"ege9", "ege10", "ege11", "ege12"} and config.get("mode") != "line":
        _, words = module.test_words_for_payload(user, config, count)
        make_question = module.make_word_question
    else:
        with connection(s) as con:
            rows = con.execute("""SELECT DISTINCT wp.word_id FROM word_progress wp JOIN users u ON u.user_id=wp.user_id
              WHERE u.teacher_id=? AND u.role='student' AND wp.due_reviews>0""", (user["user_id"],)).fetchall()
        error_words = [module.WORD_BY_ID[r[0]] for r in rows if r[0] in module.WORD_BY_ID]
        if config.get("mode") == "line":
            # The line format remains a complete mixed variant; error words add focus.
            questions = [module.make_line_question(error_words) for _ in range(count)]
            return [snapshot_question(module, activity, 'line', q) for q in questions]
        words = error_words
        if config.get("mode") != "errors":
            selected = [word for rule in config.get("rule_ids") or [] for word in module.WORDS_BY_RULE.get(rule, [])]
            seen = {w["id"] for w in words}
            words = words + [w for w in selected if w["id"] not in seen]
        if not words:
            raise ValueError("В копилках учеников пока нет подходящих ошибок.")
        random.shuffle(words)
        words = words[:count]
        make_question = module.word_question
    return [snapshot_question(module, activity, str(config.get("mode") or "errors"), make_question(word)) for word in words]


def snapshot_question(module, activity, mode, question):
    private = dict(question)
    private["correct_answer"] = private.pop("_correct_answer")
    if '_line_rows' in private:
        private['line_rows'] = private.pop('_line_rows')
    public = {k: v for k, v in question.items() if not k.startswith('_') and k not in {'explanation', 'correct_spelling', 'row_word_ids'}}
    return {"activity": activity, "mode": mode, "scope_id": module.scope_id_for(mode),
            "question_id": question["question_id"], "question": private, "public": public}


def assigned_row(con, user, test_id, allow_revoked=False):
    row = con.execute("""SELECT a.*,t.questions_json,t.title FROM assigned_test_students a
      JOIN assigned_tests t ON t.id=a.test_id WHERE a.test_id=? AND a.student_id=?""", (test_id, user["user_id"])).fetchone()
    if not row:
        raise PermissionError("Этот тест вам не назначен.")
    if row['revoked_at'] and not allow_revoked:
        raise RevokedTestError('Учитель отозвал этот тест. Новые ответы не принимаются.')
    return row


def teacher_test(con, s, user, test_id):
    s.require_teacher(user)
    test = con.execute('SELECT * FROM assigned_tests WHERE id=? AND teacher_id=?',
                       (test_id,user['user_id'])).fetchone()
    if not test:
        raise PermissionError('Этот тест принадлежит другому учителю или не существует.')
    return test


def revoke_test(s, user, payload):
    with connection(s) as con:
        con.execute('BEGIN IMMEDIATE')
        test_id = str(payload.get('test_id') or '')
        teacher_test(con,s,user,test_id)
        student_id = str(payload.get('student_id') or '')
        where = 'test_id=?'
        args = [test_id]
        if student_id:
            where += ' AND student_id=?'
            args.append(student_id)
            if not con.execute('SELECT 1 FROM assigned_test_students WHERE '+where,args).fetchone():
                raise PermissionError('Ученику не назначен этот тест.')
        con.execute('UPDATE assigned_test_students SET revoked_at=COALESCE(revoked_at,?) WHERE '+where,
                    [s.now_iso(),*args])
    return {'ok':True}


def set_deadline(s, user, payload):
    due = parse_due(payload.get('due_at'))
    with connection(s) as con:
        test_id = str(payload.get('test_id') or '')
        teacher_test(con,s,user,test_id)
        student = str(payload.get('student_id') or '')
        where,args = 'test_id=?',[test_id]
        if student:
            where += ' AND student_id=?'
            args.append(student)
        if not con.execute('SELECT 1 FROM assigned_test_students WHERE '+where,args).fetchone():
            raise PermissionError('Назначение не найдено.')
        con.execute('UPDATE assigned_test_students SET due_at=? WHERE '+where,[due,*args])
    return {'ok':True,'due_at':due}


def public_question(s, snap):
    public = {k:v for k,v in snap['public'].items() if not k.startswith('_')
              and k not in {'correct_answer','correct_spelling','explanation','row_word_ids'}}
    # Recover all visible gaps in older frozen task 15 variants, retaining the key.
    if public.get('kind') == 'ege15_sentence':
        key = snap['question']['correct_answer']
        visible = {part['target']['id'] for part in public['parts'] if 'target' in part}
        if visible != set(key):
            module = s.ege15_module
            if all(item_id in module.WORD_BY_ID for item_id in key):
                items = [{**module.WORD_BY_ID[item_id],'answer':answer} for item_id,answer in key.items()]
                public['parts'] = module.sentence_parts(module.combined_sentence(items),items)
    return public


def test_results(s, user, payload):
    with connection(s) as con:
        test_id = str(payload.get('test_id') or '')
        test = teacher_test(con,s,user,test_id)
        student_id = str(payload.get('student_id') or '')
        row = con.execute('''SELECT a.*,u.display_name FROM assigned_test_students a
            JOIN users u ON u.user_id=a.student_id WHERE a.test_id=? AND a.student_id=?''',
            (test_id,student_id)).fetchone()
        if not row:
            raise PermissionError('Ученику не назначен этот тест.')
        snapshots = json.loads(test['questions_json'])
        answers = json.loads(row['answers_json'] or '{}')
        result = json.loads(row['result_json'] or 'null')
        # Completed assignments from older versions may predate per-question checks.
        checks = {r['question_id']:r for r in (result or {}).get('results',[])}
        checks.update(checks_for(con,test_id,student_id))
        items = []
        for index,snap in enumerate(snapshots,1):
            qid = snap['question_id']
            check = checks.get(qid)
            public = public_question(s,snap)
            items.append({'number':index,'question_id':qid,'activity':snap['activity'],
                'prompt':describe_question(public),'question':public,
                'rule_name':snap['question'].get('rule_name') or '',
                'status':'checked' if check else 'draft' if qid in answers else 'unanswered',
                'given_answer':check.get('given_answer') if check else answers.get(qid),
                'correct_answer':snap['question']['correct_answer'],
                'is_correct':bool(check['is_correct']) if check else None,
                'explanation':snap['question'].get('explanation') or '',
                'correct_spelling':snap['question'].get('correct_spelling') or ''})
            items[-1]['letter_results'] = (check or {}).get('letter_results',[])
            attempt = con.execute('''SELECT attempt_id FROM attempts WHERE user_id=? AND question_id=?
                AND mode NOT LIKE '%:line_word' AND mode NOT LIKE '%:exam_word'
                AND mode NOT LIKE '%:sentence_word' ORDER BY created_at DESC LIMIT 1''',(student_id,qid)).fetchone()
            items[-1]['attempt_id'] = attempt[0] if attempt else None
        return {'test_id':test_id,'title':test['title'],'student_id':student_id,
            'student_name':row['display_name'],'completed_at':row['completed_at'],
            'revoked_at':row['revoked_at'],'total':len(snapshots),'checked':len(checks),
            'correct':sum(bool(r['is_correct']) for r in checks.values()),'items':items}


def open_test(s, user, payload):
    with connection(s) as con:
        row = assigned_row(con, user, str(payload.get("test_id") or ""), allow_revoked=True)
        if row['revoked_at'] and not row['completed_at']:
            raise RevokedTestError('Учитель отозвал этот тест. Продолжить выполнение нельзя.')
        con.execute("UPDATE assigned_test_students SET seen_at=COALESCE(seen_at,?),started_at=COALESCE(started_at,?) WHERE test_id=? AND student_id=?", (s.now_iso(), s.now_iso(), row["test_id"], user["user_id"]))
        questions = []
        for snap in json.loads(row["questions_json"]):
            public = public_question(s,snap)
            questions.append({**public, 'assignment_activity':snap['activity']})
        return {"assignment_id": row["test_id"], "title": row["title"], "questions": questions,
                'due_at':row['due_at'],'overdue':deadline_status(dict(row))['overdue'],
                "answers": json.loads(row["answers_json"] or "{}"), "result": json.loads(row["result_json"] or "null"),
                "checked_results":checks_for(con,row['test_id'],user['user_id']),
                "outline":test_outline(json.loads(row['questions_json']))}


def answer_complete(question, answer):
    kind = question['kind']
    if kind == 'error_review' and question.get('review_type') == 'paronym':
        return isinstance(answer,dict) and str(answer.get('row') or '').strip() and str(answer.get('word') or '').strip()
    if kind == 'line':
        rows = answer.get('rows') if isinstance(answer,dict) else answer
        letters = answer.get('letters',{}) if isinstance(answer,dict) else {}
        if question.get('require_letters'):
            size = sum(len(row) for row in question['rows'])
            if not isinstance(letters,dict) or any(not str(letters.get(str(i),'')).strip() for i in range(size)):
                return False
        return isinstance(rows,(str,int)) and bool(str(rows).strip())
    if kind == 'paronym_exam':
        return isinstance(answer,dict) and str(answer.get('row') or '').strip() and str(answer.get('word') or '').strip()
    if kind == 'paronym_tf':
        return isinstance(answer,dict) and (answer.get('verdict') == 'true' or
            (answer.get('verdict') == 'false' and str(answer.get('word') or '').strip()))
    if kind == 'ege14_line':
        return isinstance(answer,dict) and answer.get('mode') and (answer['mode'] != 'разное' or
            (isinstance(answer.get('words'),dict) and all(answer['words'].get(t['id']) for t in question['targets'])))
    if kind == 'ege15_sentence':
        return isinstance(answer,dict) and all(answer.get(i) for i in question['sentence_items'])
    return isinstance(answer,(str,int)) and bool(str(answer).strip())


def record_check(s, con, user, row, snap, answer, elapsed):
    if snap['question']['kind'] == 'error_review':
        from student_workspace import record_review
        result = record_review(s,con,user,snap,answer,elapsed)
    else:
        module = module_for(s, snap['activity'])
        row_answer = answer.get('rows','') if snap['question']['kind'] == 'line' and isinstance(answer,dict) else answer
        given = module.normalize_given_answer(snap['question'],row_answer) if snap['activity'] in {'ege5','ege9','ege10','ege11','ege12'} else answer
        result = module.record_attempt(con,user['user_id'],snap,snap['question_id'],snap['question'],given,elapsed)
    if snap['question']['kind'] == 'line' and isinstance(answer,dict):
        letters = answer.get('letters') or {}
        if not isinstance(letters,dict):
            raise ValueError('Некорректные буквы в строках.')
        ids = snap['question'].get('row_word_ids') or [r['word_ids'] for r in snap['question'].get('line_rows',[])]
        details = []
        for index,word_id in enumerate(i for group in ids for i in group):
            value = str(letters.get(str(index),'')).strip().lower()
            if not value:
                continue
            word = module.WORD_BY_ID[word_id]
            correct = value == word['correct_letter']
            details.append({'prompt':word['variant'],'given_answer':value,
                            'correct_answer':word['correct_letter'],'is_correct':correct})
            con.execute('''INSERT INTO attempts (attempt_id,user_id,mode,scope_id,word_id,rule_id,
                category,rule_name,question_id,prompt,given_answer,correct_answer,is_correct,created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (secrets.token_hex(12),user['user_id'],'line:line_word',snap['activity']+':letters',word_id,
                 word['rule_id'],word['category'],word['rule_name'],snap['question_id'],word['variant'],
                 value,word['correct_letter'],int(correct),s.now_iso()))
            if not correct:
                module.update_word_progress(con,user['user_id'],module.scope_id_for('errors'),word_id,0)
        result['letter_results'] = details
        if snap['question'].get('require_letters') and any(not d['is_correct'] for d in details):
            result['is_correct'] = False
            result['explanation'] = (result.get('explanation') or '') + ' В обязательной вставке букв есть ошибки.'
            con.execute('''UPDATE attempts SET is_correct=0 WHERE user_id=? AND question_id=?
                AND word_id IS NULL''',(user['user_id'],snap['question_id']))
    con.execute('INSERT INTO assigned_test_checks VALUES(?,?,?,?,?,?)',
        (row['test_id'],user['user_id'],snap['question_id'],json.dumps(answer,ensure_ascii=False),
         json.dumps(result,ensure_ascii=False),s.now_iso()))
    return result


def finish_if_complete(s, con, user, row, snapshots, answers, checks):
    if len(checks) != len(snapshots):
        return None
    results = [checks[snap['question_id']] for snap in snapshots]
    result = {'results':results,'correct':sum(bool(r['is_correct']) for r in results),'total':len(results)}
    con.execute('UPDATE assigned_test_students SET completed_at=?,answers_json=?,result_json=? WHERE test_id=? AND student_id=?',
        (s.now_iso(),json.dumps(answers,ensure_ascii=False),json.dumps(result,ensure_ascii=False),row['test_id'],user['user_id']))
    return result


def check_question(s, user, payload):
    with connection(s) as con:
        con.execute('BEGIN IMMEDIATE')
        row = assigned_row(con,user,str(payload.get('test_id') or ''))
        snapshots = json.loads(row['questions_json'])
        question_id = str(payload.get('question_id') or '')
        snap = next((snap for snap in snapshots if snap['question_id'] == question_id),None)
        if not snap:
            raise ValueError('Задание не найдено в назначенном тесте.')
        checks = checks_for(con,row['test_id'],user['user_id'])
        if row['completed_at']:
            result = json.loads(row['result_json'])
            item = next(r for r in result['results'] if r['question_id'] == question_id)
            return {'checked_result':item,'checked_results':checks,'result':result}
        answers = json.loads(row['answers_json'] or '{}')
        if question_id not in checks:
            answer = payload.get('answer')
            if not answer_complete(snap['question'],answer):
                raise ValueError('Сначала ответьте на задание.')
            elapsed = max(0,min(int(payload.get('time_spent_sec') or 0),86400))
            checks[question_id] = record_check(s,con,user,row,snap,answer,elapsed)
            answers[question_id] = answer
            con.execute('UPDATE assigned_test_students SET answers_json=?,started_at=COALESCE(started_at,?) WHERE test_id=? AND student_id=?',
                (json.dumps(answers,ensure_ascii=False),s.now_iso(),row['test_id'],user['user_id']))
        result = finish_if_complete(s,con,user,row,snapshots,answers,checks)
        return {'checked_result':checks[question_id],'checked_results':checks,'result':result}


def save_answers(s, user, payload, submit=False):
    with connection(s) as con:
        # Serializes double submits and commits attempt records together with completion.
        con.execute("BEGIN IMMEDIATE")
        row = assigned_row(con, user, str(payload.get("test_id") or ""))
        if row["completed_at"]:
            return json.loads(row["result_json"])
        answers = payload.get("answers")
        if not isinstance(answers, dict):
            raise ValueError("Некорректные ответы.")
        snapshots = json.loads(row['questions_json'])
        valid_ids = {snap['question_id'] for snap in snapshots}
        if set(answers) - valid_ids:
            raise ValueError('В ответах есть задания из другого теста.')
        merged = json.loads(row['answers_json'] or '{}')
        checked_rows = con.execute('SELECT question_id,answer_json FROM assigned_test_checks WHERE test_id=? AND student_id=?',
            (row['test_id'],user['user_id'])).fetchall()
        locked = {r['question_id']:json.loads(r['answer_json']) for r in checked_rows}
        answers = {**merged,**answers,**locked}
        if not submit:
            con.execute("UPDATE assigned_test_students SET answers_json=? WHERE test_id=? AND student_id=?", (json.dumps(answers, ensure_ascii=False), row["test_id"], user["user_id"]))
            return {"ok": True}
        elapsed = max(0, min(int(payload.get("time_spent_sec") or 0), 86400))
        checks = checks_for(con,row['test_id'],user['user_id'])
        for snap in snapshots:
            if snap['question_id'] not in checks:
                if snap['question'].get('require_letters') and not answer_complete(snap['question'],answers.get(snap['question_id'])):
                    raise ValueError('Вставьте буквы во все слова и выберите строки.')
                checks[snap['question_id']] = record_check(s,con,user,row,snap,answers.get(snap['question_id'],''),elapsed)
        return finish_if_complete(s,con,user,row,snapshots,answers,checks)


def game_result(s, user, payload):
    slug = str(payload.get("slug") or "")
    if slug not in s.HTML_GAME_TITLES and slug not in s.PUBLIC_GAMES:
        raise ValueError("Неизвестная игра.")
    event_id = str(payload.get("event_id") or "")[:100]
    if not event_id or not isinstance(payload.get("is_correct"), bool):
        raise ValueError("Некорректный результат игры.")
    text = lambda key: str(payload.get(key) if payload.get(key) is not None else "")[:20000 if key == 'prompt' else 12000]
    with connection(s) as con:
        public_id = text("public_id")
        title = s.HTML_GAME_TITLES.get(slug, slug)
        if public_id:
            game = con.execute("SELECT title FROM game_sets WHERE public_id=?", (public_id,)).fetchone()
            if not game:
                raise ValueError("Набор игры не найден.")
            title = f"{title}: {game['title']}"
        scope = "game:" + slug + (":" + public_id if public_id else "")
        inserted = con.execute("INSERT OR IGNORE INTO game_results VALUES(?,?,?,?,?)", (user["user_id"], event_id, slug, text("public_id"), s.now_iso())).rowcount
        if inserted:
            con.execute("""INSERT INTO attempts(attempt_id,user_id,mode,scope_id,rule_id,category,rule_name,
              question_id,prompt,given_answer,correct_answer,is_correct,created_at,time_spent_sec)
              VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (secrets.token_hex(12), user["user_id"], "game", scope,
              "game:" + slug, "Игры", title, event_id, text("prompt") or title,
              text("given_answer"), text("correct_answer"), int(payload["is_correct"]), s.now_iso(),
              max(0, min(int(payload.get("time_spent_sec") or 0), 86400))))
    return {"ok": True, "recorded": bool(inserted)}


def game_stats(con, user):
    where = "a.user_id=?"
    if user["role"] == "teacher":
        where = "a.user_id IN (SELECT user_id FROM users WHERE teacher_id=? AND role='student')"
    rows = con.execute(f"""SELECT u.display_name,a.user_id,a.rule_name AS game,
      COUNT(*) AS total,SUM(a.is_correct) AS correct,MAX(a.created_at) AS last_played
      FROM attempts a JOIN users u ON u.user_id=a.user_id WHERE a.mode='game' AND {where}
      GROUP BY a.user_id,a.scope_id ORDER BY last_played DESC""", (user["user_id"],)).fetchall()
    return [dict(row) for row in rows]
