from __future__ import annotations

import hashlib
import json
import random
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "task5_paronyms_lines_bank_augmented_batch03.json"
DB_PATH = ROOT / "data" / "ege_app.db"
REPEAT_ON_ERROR = 3
TASK_PROMPT = (
    "В одном из приведённых ниже предложений НЕВЕРНО употреблено выделенное слово. "
    "Исправьте лексическую ошибку, подобрав к выделенному слову пароним."
)

PRACTICE_SESSIONS: dict[str, dict[str, Any]] = {}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def db() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def normalize_text(value: Any) -> str:
    text = str(value or "").strip().lower().replace("ё", "ё")
    return " ".join(text.replace("—", "-").split())


def group_id_for(row: dict[str, Any]) -> str:
    return str(row.get("card_group_id") or make_rule_id(row.get("card_group_name") or "paronyms"))


def make_rule_id(value: str) -> str:
    return hashlib.sha1(str(value).encode("utf-8")).hexdigest()[:16]


def load_rows() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    groups: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(data.get("rows", [])):
        sentence = str(item.get("sentence") or "").strip()
        highlighted = str(item.get("highlighted_word") or "").strip()
        if not sentence or not highlighted:
            continue
        group_id = group_id_for(item)
        words = [normalize_text(word) for word in item.get("card_group_words") or [] if normalize_text(word)]
        answer = normalize_text(item.get("answer") or "")
        accepted = [normalize_text(value) for value in item.get("accepted_answers") or [] if normalize_text(value)]
        correct_word = answer if item.get("is_error") and answer else normalize_text(highlighted)
        if correct_word and correct_word not in accepted:
            accepted.insert(0, correct_word)
        if correct_word and correct_word not in words:
            words.append(correct_word)
        row = {
            "id": str(item.get("row_id") or f"paronym_row_{index:04d}"),
            "group_id": group_id,
            "category": "Паронимы",
            "rule_id": group_id,
            "rule_name": str(item.get("card_group_name") or "Паронимы"),
            "group_words": words,
            "sentence": sentence,
            "highlighted_word": highlighted,
            "is_error": bool(item.get("is_error")),
            "correct_word": correct_word,
            "accepted_answers": accepted,
            "explanation": str(item.get("explanation") or ""),
        }
        rows.append(row)
        groups.setdefault(
            group_id,
            {
                "rule_id": group_id,
                "category": "Паронимы",
                "rule_name": row["rule_name"],
                "count": 0,
            },
        )["count"] += 1
    return rows, sorted(groups.values(), key=lambda item: item["rule_name"].lower())


ROWS, RULES = load_rows()
ROW_BY_ID = {row["id"]: row for row in ROWS}
ROWS_BY_GROUP: dict[str, list[dict[str, Any]]] = {}
for row in ROWS:
    ROWS_BY_GROUP.setdefault(row["group_id"], []).append(row)
GROUP_BY_ID = {rule["rule_id"]: rule for rule in RULES}
GROUPS_BY_RULE = {rule["rule_id"]: [{"id": rule["rule_id"]}] for rule in RULES}
ERROR_ROWS = [row for row in ROWS if row["is_error"] and row["correct_word"]]
CORRECT_ROWS = [row for row in ROWS if not row["is_error"]]


def scope_id_for(mode: str, rule_id: str | None = None, rule_ids: list[str] | None = None) -> str:
    if mode == "paronym_choice":
        if rule_ids:
            digest = hashlib.sha1("|".join(sorted(rule_ids)).encode("utf-8")).hexdigest()[:16]
            return f"ege5:{mode}:groups:{digest}"
        return f"ege5:{mode}:{rule_id or 'all'}"
    if mode == "errors":
        return "ege5:errors:bank"
    return f"ege5:{mode}"


def choices_for(row: dict[str, Any]) -> list[str]:
    choices = list(dict.fromkeys(row["group_words"]))
    if row["correct_word"] and row["correct_word"] not in choices:
        choices.append(row["correct_word"])
    random.shuffle(choices)
    return choices[:6]


def sentence_with_blank(row: dict[str, Any]) -> str:
    highlighted = row["highlighted_word"]
    return row["sentence"].replace(highlighted, "_____ ", 1).replace("_____  ", "_____ ")


def public_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "row_id": row["id"],
        "sentence": row["sentence"],
        "highlighted_word": row["highlighted_word"],
        "rule_name": row["rule_name"],
    }


def make_choice_question(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "question_id": secrets.token_hex(8),
        "kind": "paronym_choice",
        "source_word_id": row["group_id"],
        "source_row_id": row["id"],
        "prompt": sentence_with_blank(row),
        "choices": choices_for(row),
        "category": row["category"],
        "rule_id": row["rule_id"],
        "rule_name": row["rule_name"],
        "explanation": row["explanation"],
        "correct_spelling": row["sentence"],
        "_correct_answer": row["correct_word"],
    }


def make_tf_question(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "question_id": secrets.token_hex(8),
        "kind": "paronym_tf",
        "source_word_id": row["group_id"],
        "source_row_id": row["id"],
        "prompt": row["sentence"],
        "category": row["category"],
        "rule_id": row["rule_id"],
        "rule_name": row["rule_name"],
        "explanation": row["explanation"],
        "correct_spelling": row["sentence"],
        "_correct_answer": f"false|{row['correct_word']}" if row["is_error"] else "true",
        "_accepted_answers": row["accepted_answers"],
        "_is_error": row["is_error"],
    }


def make_exam_question() -> dict[str, Any]:
    error_row = random.choice(ERROR_ROWS)
    used_groups = {error_row["group_id"]}
    correct_pool = [row for row in CORRECT_ROWS if row["group_id"] not in used_groups]
    correct_rows = random.sample(correct_pool, min(4, len(correct_pool)))
    rows = [error_row, *correct_rows]
    random.shuffle(rows)
    correct_index = rows.index(error_row) + 1
    return {
        "question_id": secrets.token_hex(8),
        "kind": "paronym_exam",
        "prompt": TASK_PROMPT,
        "rows": [public_row(row) for row in rows],
        "row_group_ids": [row["group_id"] for row in rows],
        "category": "Паронимы",
        "rule_id": error_row["group_id"],
        "rule_name": error_row["rule_name"],
        "explanation": error_row["explanation"],
        "correct_spelling": error_row["sentence"],
        "_correct_answer": f"{correct_index}|{error_row['correct_word']}",
        "_accepted_answers": error_row["accepted_answers"],
    }


def group_pool_for_ids(group_ids: list[str]) -> list[dict[str, Any]]:
    pool: list[dict[str, Any]] = []
    for group_id in dict.fromkeys(group_ids):
        pool.extend(ROWS_BY_GROUP.get(group_id, []))
    return pool


def pick_rows_for_scope(user_id: str, scope_id: str, pool: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    if not pool:
        return []
    pool_by_group: dict[str, list[dict[str, Any]]] = {}
    for row in pool:
        pool_by_group.setdefault(row["group_id"], []).append(row)
    selected: list[dict[str, Any]] = []
    with db() as con:
        due_rows = con.execute(
            """
            SELECT word_id
            FROM word_progress
            WHERE user_id = ? AND scope_id = ? AND due_reviews > 0
            ORDER BY due_reviews DESC, error_count DESC, last_seen_at ASC
            """,
            (user_id, scope_id_for("errors")),
        ).fetchall()
        for due in due_rows:
            rows = pool_by_group.get(due["word_id"])
            if rows:
                selected.append(random.choice(rows))
            if len(selected) >= count:
                return selected
    rest = [row for row in pool if row["group_id"] not in {item["group_id"] for item in selected}]
    random.shuffle(rest)
    return selected + rest[: max(0, count - len(selected))]


def error_bank_rows(user_id: str) -> list[dict[str, Any]]:
    with db() as con:
        rows = con.execute(
            """
            SELECT word_id
            FROM word_progress
            WHERE user_id = ? AND scope_id = ? AND due_reviews > 0
            ORDER BY due_reviews DESC, error_count DESC, last_seen_at DESC
            """,
            (user_id, scope_id_for("errors")),
        ).fetchall()
    pool = []
    for item in rows:
        group_rows = ROWS_BY_GROUP.get(item["word_id"], [])
        if group_rows:
            pool.append(random.choice(group_rows))
    return pool


def update_word_progress(con: sqlite3.Connection, user_id: str, scope_id: str, word_id: str, is_correct: int) -> None:
    row = con.execute(
        "SELECT * FROM word_progress WHERE user_id = ? AND scope_id = ? AND word_id = ?",
        (user_id, scope_id, word_id),
    ).fetchone()
    if row:
        due_reviews = int(row["due_reviews"] or 0)
        correct_count = int(row["correct_count"] or 0)
        error_count = int(row["error_count"] or 0)
        if is_correct:
            correct_count += 1
            due_reviews = max(0, due_reviews - 1)
        else:
            correct_count = 0
            error_count += 1
            due_reviews = REPEAT_ON_ERROR
        con.execute(
            """
            UPDATE word_progress
            SET cycle_seen = 1, due_reviews = ?, correct_count = ?, error_count = ?, last_seen_at = ?
            WHERE user_id = ? AND scope_id = ? AND word_id = ?
            """,
            (due_reviews, correct_count, error_count, now_iso(), user_id, scope_id, word_id),
        )
    else:
        con.execute(
            """
            INSERT INTO word_progress
                (user_id, scope_id, word_id, cycle_seen, due_reviews, correct_count, error_count, last_seen_at)
            VALUES (?, ?, ?, 1, ?, ?, ?, ?)
            """,
            (user_id, scope_id, word_id, 0 if is_correct else REPEAT_ON_ERROR, 1 if is_correct else 0, 0 if is_correct else 1, now_iso()),
        )


def normalize_given_answer(question: dict[str, Any], value: Any) -> str:
    if question.get("kind") == "paronym_exam":
        if isinstance(value, dict):
            return f"{str(value.get('row') or '').strip()}|{normalize_text(value.get('word'))}"
        raw = str(value or "").strip()
        if "|" in raw:
            row, word = raw.split("|", 1)
            return f"{row.strip()}|{normalize_text(word)}"
        return raw
    if question.get("kind") == "paronym_tf":
        if isinstance(value, dict):
            verdict = "true" if value.get("verdict") == "true" else "false"
            word = normalize_text(value.get("word"))
            return verdict if verdict == "true" else f"false|{word}"
        return normalize_text(value)
    return normalize_text(value)


def question_is_correct(question: dict[str, Any], given: str) -> bool:
    correct = normalize_given_answer(question, question["correct_answer"])
    if question.get("kind") == "paronym_exam":
        given_row, _, given_word = given.partition("|")
        correct_row, _, _ = correct.partition("|")
        return given_row == correct_row and given_word in question.get("accepted_answers", [])
    if question.get("kind") == "paronym_tf":
        if correct == "true":
            return given == "true"
        verdict, _, word = given.partition("|")
        return verdict == "false" and word in question.get("accepted_answers", [])
    return given == correct or given in question.get("accepted_answers", [])


def record_attempt(
    con: sqlite3.Connection,
    user_id: str,
    session: dict[str, Any],
    question_id: str,
    question: dict[str, Any],
    given: str,
    elapsed: Any = None,
) -> dict[str, Any]:
    is_correct = int(question_is_correct(question, given))
    correct = normalize_given_answer(question, question["correct_answer"])
    group_id = question.get("source_word_id")
    affected_group_ids = [group_id] if group_id else []
    if question.get("kind") == "paronym_exam":
        affected_group_ids = question.get("row_group_ids") or []
    for affected in dict.fromkeys(affected_group_ids):
        if not affected:
            continue
        if session["scope_id"] != scope_id_for("errors"):
            update_word_progress(con, user_id, session["scope_id"], affected, is_correct)
        update_word_progress(con, user_id, scope_id_for("errors"), affected, is_correct)
    con.execute(
        """
        INSERT INTO attempts
            (attempt_id, user_id, mode, scope_id, word_id, rule_id, category, rule_name,
             question_id, prompt, given_answer, correct_answer, is_correct, created_at, time_spent_sec)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            secrets.token_hex(12),
            user_id,
            session["mode"],
            session["scope_id"],
            group_id or question.get("rule_id"),
            question.get("rule_id"),
            question.get("category"),
            question.get("rule_name"),
            question_id,
            question.get("prompt"),
            given,
            correct,
            is_correct,
            now_iso(),
            elapsed,
        ),
    )
    return {
        "question_id": question_id,
        "is_correct": bool(is_correct),
        "given_answer": given,
        "correct_answer": correct,
        "explanation": question.get("explanation"),
        "correct_spelling": question.get("correct_spelling"),
    }


def start_practice(user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    mode = str(payload.get("mode") or "paronym_choice")
    count = max(1, min(int(payload.get("count") or 10), 30))
    if mode == "paronym_choice":
        rule_ids = [str(rule_id) for rule_id in payload.get("rule_ids", []) if str(rule_id) in ROWS_BY_GROUP]
        pool = group_pool_for_ids(rule_ids) if rule_ids else list(ROWS)
        scope_id = scope_id_for(mode, rule_ids=rule_ids or [rule["rule_id"] for rule in RULES])
        questions = [make_choice_question(row) for row in pick_rows_for_scope(user["user_id"], scope_id, pool, min(count, len(pool)))]
    elif mode == "paronym_exam":
        scope_id = scope_id_for(mode)
        questions = [make_exam_question() for _ in range(count)]
    elif mode == "paronym_tf":
        scope_id = scope_id_for(mode)
        questions = [make_tf_question(row) for row in pick_rows_for_scope(user["user_id"], scope_id, ROWS, min(count, len(ROWS)))]
    elif mode == "errors":
        scope_id = scope_id_for(mode)
        pool = error_bank_rows(user["user_id"])
        if not pool:
            raise ValueError("Копилка ошибок пока пуста.")
        questions = [make_tf_question(row) for row in pool[: min(count, len(pool))]]
    else:
        raise ValueError("Неизвестный режим тренировки.")

    session_id = secrets.token_hex(12)
    answer_key: dict[str, dict[str, Any]] = {}
    public_questions = []
    for question in questions:
        correct_answer = question.pop("_correct_answer", "")
        accepted = question.pop("_accepted_answers", None)
        question.pop("_is_error", None)
        answer_key[question["question_id"]] = {
            **question,
            "correct_answer": normalize_given_answer(question, correct_answer),
            "accepted_answers": accepted or [normalize_text(correct_answer)],
        }
        question.pop("row_group_ids", None)
        public_questions.append(question)
    PRACTICE_SESSIONS[session_id] = {
        "user_id": user["user_id"],
        "mode": mode,
        "scope_id": scope_id,
        "started_at": now_iso(),
        "questions": answer_key,
        "answered": {},
    }
    return {"session_id": session_id, "questions": public_questions}


def check_practice_answer(user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    session_id = payload.get("session_id")
    question_id = str(payload.get("question_id") or "")
    session = PRACTICE_SESSIONS.get(session_id)
    if not session or session["user_id"] != user["user_id"]:
        raise ValueError("Сессия тренировки не найдена.")
    question = session["questions"].get(question_id)
    if not question:
        raise ValueError("Вопрос не найден.")
    if question_id in session["answered"]:
        return session["answered"][question_id]
    given = normalize_given_answer(question, payload.get("answer", ""))
    with db() as con:
        result = record_attempt(con, user["user_id"], session, question_id, question, given, payload.get("time_spent_sec"))
    session["answered"][question_id] = result
    if len(session["answered"]) >= len(session["questions"]):
        PRACTICE_SESSIONS.pop(session_id, None)
    return result


def submit_practice(user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    session_id = payload.get("session_id")
    answers = payload.get("answers") or {}
    elapsed = payload.get("time_spent_sec")
    session = PRACTICE_SESSIONS.get(session_id)
    if not session or session["user_id"] != user["user_id"]:
        raise ValueError("Сессия тренировки не найдена.")
    results = []
    with db() as con:
        for question_id, question in session["questions"].items():
            if question_id in session.get("answered", {}):
                results.append(session["answered"][question_id])
                continue
            given = normalize_given_answer(question, answers.get(question_id, ""))
            results.append(record_attempt(con, user["user_id"], session, question_id, question, given, elapsed))
    PRACTICE_SESSIONS.pop(session_id, None)
    return {
        "results": results,
        "correct": sum(1 for result in results if result["is_correct"]),
        "total": len(results),
    }
