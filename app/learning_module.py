"""Persistent teacher assignments and authenticated game results."""
import json
import secrets
import random
from contextlib import contextmanager, closing


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
    """)


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
            tests = [dict(r) for r in con.execute("SELECT id,title,created_at FROM assigned_tests WHERE teacher_id=? ORDER BY created_at DESC", (user["user_id"],))]
            for test in tests:
                test["students"] = [dict(r) for r in con.execute("""SELECT a.student_id,u.display_name,a.started_at,a.completed_at,a.result_json
                  FROM assigned_test_students a JOIN users u ON u.user_id=a.student_id WHERE a.test_id=?""", (test["id"],))]
                for student in test["students"]:
                    result = json.loads(student.pop("result_json") or "null")
                    student["result"] = result
            return {"students": students, "groups": groups, "tests": tests}
        tests = [dict(r) for r in con.execute("""SELECT t.id,t.title,t.created_at,u.display_name AS teacher_name,
          a.seen_at,a.started_at,a.completed_at,a.result_json FROM assigned_tests t
          JOIN assigned_test_students a ON a.test_id=t.id JOIN users u ON u.user_id=t.teacher_id
          WHERE a.student_id=? ORDER BY t.created_at DESC""", (user["user_id"],))]
        for test in tests:
            test["result"] = json.loads(test.pop("result_json") or "null")
        return {"tests": tests, "unread": sum(not t["seen_at"] and not t["completed_at"] for t in tests),
                "pending": sum(not t["completed_at"] for t in tests)}


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
    test_id = secrets.token_hex(12)
    with connection(s) as con:
        con.execute("INSERT INTO assigned_tests VALUES(?,?,?,?,?)", (test_id, user["user_id"], title, json.dumps(snapshots, ensure_ascii=False), s.now_iso()))
        con.executemany("INSERT INTO assigned_test_students(test_id,student_id) VALUES(?,?)", [(test_id, i) for i in ids])
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
    public = {k: v for k, v in question.items() if not k.startswith('_') and k not in {'explanation', 'correct_spelling', 'row_word_ids'}}
    return {"activity": activity, "mode": mode, "scope_id": module.scope_id_for(mode),
            "question_id": question["question_id"], "question": private, "public": public}


def assigned_row(con, user, test_id):
    row = con.execute("""SELECT a.*,t.questions_json,t.title FROM assigned_test_students a
      JOIN assigned_tests t ON t.id=a.test_id WHERE a.test_id=? AND a.student_id=?""", (test_id, user["user_id"])).fetchone()
    if not row:
        raise PermissionError("Этот тест вам не назначен.")
    return row


def open_test(s, user, payload):
    with connection(s) as con:
        row = assigned_row(con, user, str(payload.get("test_id") or ""))
        con.execute("UPDATE assigned_test_students SET seen_at=COALESCE(seen_at,?),started_at=COALESCE(started_at,?) WHERE test_id=? AND student_id=?", (s.now_iso(), s.now_iso(), row["test_id"], user["user_id"]))
        questions = []
        for snap in json.loads(row["questions_json"]):
            questions.append(snap["public"])
        return {"assignment_id": row["test_id"], "title": row["title"], "questions": questions,
                "answers": json.loads(row["answers_json"] or "{}"), "result": json.loads(row["result_json"] or "null")}


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
        if not submit:
            con.execute("UPDATE assigned_test_students SET answers_json=? WHERE test_id=? AND student_id=?", (json.dumps(answers, ensure_ascii=False), row["test_id"], user["user_id"]))
            return {"ok": True}
        elapsed = max(0, min(int(payload.get("time_spent_sec") or 0), 86400))
        results = []
        for snap in json.loads(row["questions_json"]):
            module = module_for(s, snap["activity"])
            question = snap["question"]
            given = answers.get(snap["question_id"], "")
            if snap["activity"] in {"ege5", "ege9", "ege10", "ege11", "ege12"}:
                given = module.normalize_given_answer(question, given)
            results.append(module.record_attempt(con, user["user_id"], snap, snap["question_id"], question, given, elapsed))
        result = {"results": results, "correct": sum(bool(r["is_correct"]) for r in results), "total": len(results)}
        con.execute("UPDATE assigned_test_students SET completed_at=?,answers_json=?,result_json=? WHERE test_id=? AND student_id=?", (s.now_iso(), json.dumps(answers, ensure_ascii=False), json.dumps(result, ensure_ascii=False), row["test_id"], user["user_id"]))
        return result


def game_result(s, user, payload):
    slug = str(payload.get("slug") or "")
    if slug not in s.HTML_GAME_TITLES and slug not in s.PUBLIC_GAMES:
        raise ValueError("Неизвестная игра.")
    event_id = str(payload.get("event_id") or "")[:100]
    if not event_id or not isinstance(payload.get("is_correct"), bool):
        raise ValueError("Некорректный результат игры.")
    text = lambda key: str(payload.get(key) or "")[:2000]
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
