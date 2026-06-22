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
WORDS_PATH = ROOT / "task_14_trainer_navigation.json"
DB_PATH = ROOT / "data" / "ege_app.db"
REPEAT_ON_ERROR = 3
SPELLING_TYPES = ("слитно", "раздельно", "дефис")
PRACTICE_SESSIONS: dict[str, dict[str, Any]] = {}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def db() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def make_rule_id(category: str, spelling: str) -> str:
    return hashlib.sha1(f"{category}::{spelling}".encode("utf-8")).hexdigest()[:16]


def normalize_spelling(value: Any) -> str:
    text = str(value or "").strip().lower().replace("через дефис", "дефис")
    return text if text in SPELLING_TYPES else ""


def load_data() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    data = json.loads(WORDS_PATH.read_text(encoding="utf-8-sig"))
    raw_lines = data.get("lines") or []
    raw_cards = data.get("cards") or []
    lines_by_id = {str(line["line_id"]): dict(line) for line in raw_lines}
    words: list[dict[str, Any]] = []
    for card in raw_cards:
        navigation = card.get("navigation") or {}
        category = str(navigation.get("main_section") or card.get("part_of_speech") or "Прочее").strip()
        spelling = normalize_spelling(card.get("answer_type"))
        if not spelling:
            continue
        rule_id = make_rule_id(category, spelling)
        line = lines_by_id.get(str(card.get("parent_line_id"))) or {}
        words.append(
            {
                "id": str(card.get("item_id")),
                "line_id": str(card.get("parent_line_id")),
                "position_index": int(card.get("position_index") or 0),
                "category": category,
                "rule_id": rule_id,
                "rule_name": f"{category}: {spelling}",
                "variant": str(card.get("target_normalized") or ""),
                "context": str((card.get("context") or {}).get("line_text") or line.get("line_text") or ""),
                "correct_letter": spelling,
                "answer": spelling,
                "correct_spelling": str(card.get("correct_spelling") or ""),
                "explanation": str(card.get("explanation") or card.get("subrule") or ""),
                "part_of_speech": str(card.get("part_of_speech") or ""),
            }
        )
    word_by_id = {word["id"]: word for word in words}
    lines: list[dict[str, Any]] = []
    for line in raw_lines:
        item_ids = [str(item_id) for item_id in line.get("item_ids") or [] if str(item_id) in word_by_id]
        if not item_ids:
            continue
        line_copy = dict(line)
        line_copy["item_ids"] = item_ids
        line_copy["answer_types"] = [word_by_id[item_id]["answer"] for item_id in item_ids]
        line_copy["instruction"] = ""
        first = word_by_id[item_ids[0]]
        for card in raw_cards:
            if str(card.get("item_id")) == first["id"]:
                line_copy["instruction"] = str((card.get("context") or {}).get("task_instruction") or "")
                break
        lines.append(line_copy)
    counts: dict[tuple[str, str], int] = {}
    for word in words:
        key = (word["category"], word["answer"])
        counts[key] = counts.get(key, 0) + 1
    rules = [
        {"rule_id": make_rule_id(category, spelling), "category": category, "rule_name": f"{category}: {spelling}", "count": count}
        for (category, spelling), count in sorted(counts.items())
    ]
    return words, lines, rules


WORDS, LINES, RULES = load_data()
WORD_BY_ID = {word["id"]: word for word in WORDS}
LINE_BY_ID = {line["line_id"]: line for line in LINES}
WORDS_BY_RULE: dict[str, list[dict[str, Any]]] = {}
for word in WORDS:
    WORDS_BY_RULE.setdefault(word["rule_id"], []).append(word)


def scope_id_for(mode: str, rule_id: str | None = None, rule_ids: list[str] | None = None) -> str:
    if mode in {"word_context", "rule"} and (rule_ids or rule_id):
        selected = rule_ids or [str(rule_id)]
        digest = hashlib.sha1("|".join(sorted(selected)).encode("utf-8")).hexdigest()[:16]
        return f"word_context:rules:{digest}"
    if mode == "errors":
        return "errors:bank"
    return mode


def letter_choices(word: dict[str, Any]) -> list[str]:
    choices = list(SPELLING_TYPES)
    random.shuffle(choices)
    return choices


def solved_word_ids_for_pool(con: sqlite3.Connection, user_id: str, word_ids: list[str]) -> set[str]:
    if not word_ids:
        return set()
    solved: set[str] = set()
    for start in range(0, len(word_ids), 700):
        chunk = word_ids[start:start + 700]
        marks = ",".join("?" for _ in chunk)
        rows = con.execute(
            f"SELECT DISTINCT word_id FROM word_progress WHERE user_id=? AND due_reviews=0 AND cycle_seen=1 AND word_id IN ({marks})",
            (user_id, *chunk),
        ).fetchall()
        solved.update(row["word_id"] for row in rows)
    return solved


def pick_words(user_id: str, scope_id: str, pool: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    if not pool:
        return []
    unique = {word["id"]: word for word in pool}
    with db() as con:
        due_rows = con.execute(
            "SELECT word_id FROM word_progress WHERE user_id=? AND scope_id=? AND due_reviews>0 ORDER BY due_reviews DESC,last_seen_at",
            (user_id, "ege14:errors:bank"),
        ).fetchall()
        selected = [unique[row["word_id"]] for row in due_rows if row["word_id"] in unique][:count]
        selected_ids = {word["id"] for word in selected}
        solved = solved_word_ids_for_pool(con, user_id, list(unique))
    fresh = [word for word in unique.values() if word["id"] not in selected_ids and word["id"] not in solved]
    if len(fresh) < count - len(selected):
        fresh.extend(word for word in unique.values() if word["id"] not in selected_ids and word not in fresh)
    random.shuffle(fresh)
    return selected + fresh[: max(0, count - len(selected))]


def word_question(word: dict[str, Any]) -> dict[str, Any]:
    return {
        "question_id": secrets.token_hex(8),
        "kind": "ege14_word",
        "source_word_id": word["id"],
        "prompt": word["context"],
        "target": word["variant"],
        "choices": list(SPELLING_TYPES),
        "category": word["category"],
        "rule_id": word["rule_id"],
        "rule_name": word["rule_name"],
        "explanation": word["explanation"],
        "correct_spelling": word["correct_spelling"],
        "_correct_answer": word["answer"],
    }


def line_question(line: dict[str, Any]) -> dict[str, Any]:
    words = [WORD_BY_ID[item_id] for item_id in line["item_ids"]]
    same = len(set(line["answer_types"])) == 1
    correct = line["answer_types"][0] if same else "разное"
    return {
        "question_id": secrets.token_hex(8),
        "kind": "ege14_line",
        "prompt": line["line_text"],
        "targets": [{"id": word["id"], "target": word["variant"]} for word in words],
        "choices": [*SPELLING_TYPES, "разное"],
        "category": "Строка",
        "rule_id": "ege14_line",
        "rule_name": "Строка",
        "explanation": "; ".join(word["explanation"] for word in words),
        "correct_spelling": "; ".join(word["correct_spelling"] for word in words),
        "_correct_answer": correct,
        "_word_answers": {word["id"]: word["answer"] for word in words},
    }


def instruction_target(instruction: str) -> str:
    upper = instruction.upper()
    if "РАЗДЕЛЬНО" in upper:
        return "раздельно"
    if "ДЕФИС" in upper:
        return "дефис"
    return "слитно"


def exam_groups() -> list[list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for line in LINES:
        source = line.get("source_address") or {}
        key = str(source.get("variant_id") or "")
        grouped.setdefault(key, []).append(line)
    result = []
    for lines in grouped.values():
        ordered = sorted(lines, key=lambda line: int((line.get("source_address") or {}).get("line_number") or 0))
        if len(ordered) != 5:
            continue
        target = instruction_target(ordered[0].get("instruction") or "")
        correct_count = sum(1 for line in ordered if line.get("line_answer_type") == target)
        if 2 <= correct_count <= 4:
            result.append(ordered)
    return result


EXAM_GROUPS = exam_groups()


def exam_question(lines: list[dict[str, Any]]) -> dict[str, Any]:
    target = instruction_target(lines[0].get("instruction") or "")
    correct_indexes = [str(index + 1) for index, line in enumerate(lines) if line.get("line_answer_type") == target]
    return {
        "question_id": secrets.token_hex(8),
        "kind": "ege14_exam",
        "prompt": f"Укажите варианты ответов, в которых оба выделенных слова пишутся {target.upper()}.",
        "rows": [line["line_text"] for line in lines],
        "category": "Формат ЕГЭ",
        "rule_id": "ege14_exam",
        "rule_name": f"Оба слова — {target}",
        "explanation": f"Правильные строки: {', '.join(correct_indexes)}.",
        "correct_spelling": "; ".join(
            WORD_BY_ID[item_id]["correct_spelling"] for line in lines for item_id in line["item_ids"]
        ),
        "_correct_answer": "".join(correct_indexes),
        "_exam_rows": [{"item_ids": line["item_ids"]} for line in lines],
    }


def error_bank_words(user_id: str) -> list[dict[str, Any]]:
    with db() as con:
        rows = con.execute(
            "SELECT word_id,MAX(created_at) last_error FROM attempts WHERE user_id=? AND is_correct=0 AND word_id IS NOT NULL GROUP BY word_id ORDER BY last_error DESC",
            (user_id,),
        ).fetchall()
    return [WORD_BY_ID[row["word_id"]] for row in rows if row["word_id"] in WORD_BY_ID]


def start_practice(user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    mode = str(payload.get("mode") or "word_context")
    count = max(1, min(int(payload.get("count") or 10), 30))
    if mode == "word_context":
        rule_ids = [str(value) for value in payload.get("rule_ids") or [] if str(value) in WORDS_BY_RULE]
        pool = [word for rule_id in dict.fromkeys(rule_ids) for word in WORDS_BY_RULE[rule_id]]
        if not pool:
            raise ValueError("Выберите хотя бы одну подрубрику.")
        scope = scope_id_for(mode, rule_ids=rule_ids)
        questions = [word_question(word) for word in pick_words(user["user_id"], scope, pool, min(count, len(pool)))]
    elif mode == "line_spelling":
        scope = scope_id_for(mode)
        picked = random.sample(LINES, min(count, len(LINES)))
        questions = [line_question(line) for line in picked]
    elif mode == "exam":
        scope = scope_id_for(mode)
        if not EXAM_GROUPS:
            raise ValueError("В базе нет полных вариантов для формата ЕГЭ.")
        picked_groups = random.sample(EXAM_GROUPS, min(count, len(EXAM_GROUPS)))
        questions = [exam_question(group) for group in picked_groups]
    elif mode == "errors":
        scope = scope_id_for(mode)
        pool = error_bank_words(user["user_id"])
        if not pool:
            raise ValueError("Копилка ошибок пока пуста.")
        questions = [word_question(word) for word in pick_words(user["user_id"], scope, pool, min(count, len(pool)))]
    else:
        raise ValueError("Неизвестный режим тренировки.")

    session_id = secrets.token_hex(12)
    private: dict[str, dict[str, Any]] = {}
    public = []
    for question in questions:
        item = dict(question)
        item["correct_answer"] = item.pop("_correct_answer")
        if "_word_answers" in item:
            item["word_answers"] = item.pop("_word_answers")
        if "_exam_rows" in item:
            item["exam_rows"] = item.pop("_exam_rows")
        private[item["question_id"]] = item
        public.append({key: value for key, value in item.items() if key not in {"correct_answer", "word_answers", "exam_rows"}})
    PRACTICE_SESSIONS[session_id] = {"user_id": user["user_id"], "mode": mode, "scope_id": scope, "questions": private}
    return {"session_id": session_id, "questions": public}


def update_progress(con: sqlite3.Connection, user_id: str, scope: str, word_id: str, correct: bool) -> None:
    row = con.execute(
        "SELECT due_reviews,correct_count,error_count FROM word_progress WHERE user_id=? AND scope_id=? AND word_id=?",
        (user_id, scope, word_id),
    ).fetchone()
    due = int(row["due_reviews"] or 0) if row else 0
    good = int(row["correct_count"] or 0) if row else 0
    bad = int(row["error_count"] or 0) if row else 0
    if correct:
        due, good, seen = max(0, due - 1), good + 1, 1
    else:
        due, bad, seen = REPEAT_ON_ERROR, bad + 1, 0
    con.execute(
        """INSERT INTO word_progress(user_id,scope_id,word_id,cycle_seen,due_reviews,correct_count,error_count,last_seen_at)
        VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(user_id,scope_id,word_id) DO UPDATE SET
        cycle_seen=excluded.cycle_seen,due_reviews=excluded.due_reviews,correct_count=excluded.correct_count,
        error_count=excluded.error_count,last_seen_at=excluded.last_seen_at""",
        (user_id, scope, word_id, seen, due, good, bad, now_iso()),
    )


def normalize_answer(question: dict[str, Any], raw: Any) -> Any:
    if question["kind"] == "ege14_line":
        if not isinstance(raw, dict):
            return {"mode": normalize_spelling(raw), "words": {}}
        return {
            "mode": str(raw.get("mode") or "").strip().lower(),
            "words": {str(key): normalize_spelling(value) for key, value in (raw.get("words") or {}).items()},
        }
    if question["kind"] == "ege14_exam":
        return "".join(sorted(set(char for char in str(raw or "") if char in "12345")))
    return normalize_spelling(raw)


def insert_attempt(con: sqlite3.Connection, user_id: str, session: dict[str, Any], question: dict[str, Any],
                   question_id: str, given: str, correct: str, is_correct: bool, word_id: str | None,
                   elapsed: Any = None, mode_suffix: str = "") -> None:
    word = WORD_BY_ID.get(word_id or "")
    con.execute(
        """INSERT INTO attempts(attempt_id,user_id,mode,scope_id,word_id,rule_id,category,rule_name,
        question_id,prompt,given_answer,correct_answer,is_correct,created_at,time_spent_sec)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (secrets.token_hex(12), user_id, session["mode"] + mode_suffix, session["scope_id"], word_id,
         word["rule_id"] if word else question.get("rule_id"), word["category"] if word else question.get("category"),
         word["rule_name"] if word else question.get("rule_name"), question_id,
         word["context"] if word else question.get("prompt"), given, correct, int(is_correct), now_iso(), elapsed),
    )


def record_attempt(con: sqlite3.Connection, user_id: str, session: dict[str, Any], question_id: str,
                   question: dict[str, Any], raw: Any, elapsed: Any = None) -> dict[str, Any]:
    given = normalize_answer(question, raw)
    correct = question["correct_answer"]
    word_id = question.get("source_word_id")
    if question["kind"] == "ege14_line":
        word_answers = question["word_answers"]
        mode = given["mode"]
        word_given = given["words"]
        if correct == "разное":
            is_correct = mode == "разное" and all(word_given.get(item_id) == answer for item_id, answer in word_answers.items())
        else:
            is_correct = mode == correct
        for item_id, answer in word_answers.items():
            item_given = word_given.get(item_id) if mode == "разное" else mode
            item_correct = item_given == answer
            if not item_correct:
                update_progress(con, user_id, "ege14:errors:bank", item_id, False)
                insert_attempt(con, user_id, session, question, question_id, item_given or "—", answer, False, item_id, elapsed, ":line_word")
        display_given = mode if mode != "разное" else "разное: " + ", ".join(word_given.values())
    elif question["kind"] == "ege14_exam":
        is_correct = given == correct
        wrong_rows = set(given).symmetric_difference(set(correct))
        for row_number in wrong_rows:
            row_index = int(row_number) - 1
            for item_id in question["exam_rows"][row_index]["item_ids"]:
                answer = WORD_BY_ID[item_id]["answer"]
                update_progress(con, user_id, "ege14:errors:bank", item_id, False)
                insert_attempt(con, user_id, session, question, question_id, given or "—", answer, False, item_id, elapsed, ":exam_word")
        display_given = given
    else:
        is_correct = given == correct
        display_given = given
        if word_id:
            update_progress(con, user_id, session["scope_id"], word_id, is_correct)
            if not is_correct and session["scope_id"] != "ege14:errors:bank":
                update_progress(con, user_id, "ege14:errors:bank", word_id, False)
    insert_attempt(con, user_id, session, question, question_id, str(display_given or "—"), str(correct), is_correct, word_id, elapsed)
    return {
        "question_id": question_id,
        "is_correct": bool(is_correct),
        "given_answer": display_given,
        "correct_answer": correct,
        "explanation": question.get("explanation"),
        "correct_spelling": question.get("correct_spelling"),
    }


def submit_practice(user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    session_id = str(payload.get("session_id") or "")
    session = PRACTICE_SESSIONS.get(session_id)
    if not session or session["user_id"] != user["user_id"]:
        raise ValueError("Сессия тренировки не найдена.")
    answers = payload.get("answers") or {}
    results = []
    with db() as con:
        for question_id, question in session["questions"].items():
            results.append(record_attempt(con, user["user_id"], session, question_id, question, answers.get(question_id), payload.get("time_spent_sec")))
    PRACTICE_SESSIONS.pop(session_id, None)
    return {"results": results, "correct": sum(result["is_correct"] for result in results), "total": len(results)}


def check_practice_answer(user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    raise ValueError("Для задания 14 ответы проверяются после завершения тренировки.")


def build_test_file(user: dict[str, Any], payload: dict[str, Any]) -> tuple[bytes, str, str]:
    if user.get("role") != "teacher":
        raise PermissionError("Функция доступна только учителю.")
    count = max(1, min(int(payload.get("count") or 10), 60))
    mode = str(payload.get("mode") or "word_context")
    lines = ["ЕГЭ. Задание 14", ""]
    answers = ["", "Ответы", ""]
    if mode == "exam":
        for index, group in enumerate(random.sample(EXAM_GROUPS, min(count, len(EXAM_GROUPS))), 1):
            question = exam_question(group)
            lines.append(f"{index}. {question['prompt']}")
            lines.extend(f"   {row_index}) {row}" for row_index, row in enumerate(question["rows"], 1))
            lines.append("")
            answers.append(f"{index}. {question['_correct_answer']}")
    elif mode == "line_spelling":
        for index, line in enumerate(random.sample(LINES, min(count, len(LINES))), 1):
            question = line_question(line)
            lines.append(f"{index}. {question['prompt']}")
            answers.append(f"{index}. {question['_correct_answer']} — {question['correct_spelling']}")
    else:
        if mode == "errors":
            with db() as con:
                rows = con.execute(
                    """SELECT a.word_id,MAX(a.created_at) last_error FROM attempts a
                    JOIN users u ON u.user_id=a.user_id WHERE u.teacher_id=? AND a.is_correct=0
                    AND a.word_id IS NOT NULL GROUP BY a.word_id ORDER BY last_error DESC""",
                    (user["user_id"],),
                ).fetchall()
            pool = [WORD_BY_ID[row["word_id"]] for row in rows if row["word_id"] in WORD_BY_ID]
        else:
            rule_ids = [str(value) for value in payload.get("rule_ids") or [] if str(value) in WORDS_BY_RULE]
            pool = [word for rule_id in dict.fromkeys(rule_ids) for word in WORDS_BY_RULE[rule_id]]
        if not pool:
            raise ValueError("Нет слов для составления теста.")
        random.shuffle(pool)
        selected = pool[:count]
        lines.extend(f"{index}. {word['context']}" for index, word in enumerate(selected, 1))
        answers.extend(f"{index}. {word['correct_spelling']} — {word['answer']}" for index, word in enumerate(selected, 1))
    return ("\n".join(lines + answers) + "\n").encode("utf-8"), "ege14_test.txt", "text/plain; charset=utf-8"
