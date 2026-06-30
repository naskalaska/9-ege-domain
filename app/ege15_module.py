from __future__ import annotations

import hashlib
import json
import random
import re
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
WORDS_PATH = ROOT / "task_15_word_cards_v10_checked.json"
DB_PATH = ROOT / "data" / "ege_app.db"
REPEAT_ON_ERROR = 3
SPELLING_TYPES = ("Н", "НН")
PRACTICE_SESSIONS: dict[str, dict[str, Any]] = {}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def db() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def make_rule_id(category: str) -> str:
    return hashlib.sha1(category.encode("utf-8")).hexdigest()[:16]


def normalize_answer(value: Any) -> str:
    text = str(value or "").strip().upper().replace("1", "Н").replace("2", "НН")
    return text if text in SPELLING_TYPES else ""


def sentence_key(card: dict[str, Any]) -> str:
    return re.sub(r", пропуск.*$", "", str(card.get("source") or "")).strip()


def gap_label(sentence: str) -> str:
    match = re.search(r"\S*\.\.\S*", sentence)
    return match.group(0) if match else ""


def load_data() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    data = json.loads(WORDS_PATH.read_text(encoding="utf-8-sig"))
    words: list[dict[str, Any]] = []
    for card in data.get("cards") or []:
        category = str(card.get("part_of_speech") or card.get("orthogram_group") or "Прочее").strip()
        answer = normalize_answer(card.get("answer"))
        if not answer:
            continue
        context = card.get("context") or {}
        rule_id = make_rule_id(category)
        words.append(
            {
                "id": str(card.get("id")),
                "category": category,
                "rule_id": rule_id,
                "rule_name": category,
                "variant": str(card.get("word") or ""),
                "context": str(context.get("source_sentence") or card.get("word") or ""),
                "gap_label": gap_label(str(context.get("source_sentence") or card.get("word") or "")),
                "answer": answer,
                "correct_spelling": str(card.get("answer_word") or ""),
                "explanation": str(card.get("explanation") or ""),
                "sentence_key": sentence_key(card),
            }
        )
    groups: dict[str, list[dict[str, Any]]] = {}
    for word in words:
        groups.setdefault(word["sentence_key"], []).append(word)
    sentence_groups = [
        {"line_id": key, "items": items}
        for key, items in groups.items()
        if key and len(items) >= 2
    ]
    counts: dict[str, int] = {}
    for word in words:
        counts[word["category"]] = counts.get(word["category"], 0) + 1
    rules = [
        {"rule_id": make_rule_id(category), "category": category, "rule_name": category, "count": count}
        for category, count in sorted(counts.items())
    ]
    return words, sentence_groups, rules


WORDS, SENTENCES, RULES = load_data()
WORD_BY_ID = {word["id"]: word for word in WORDS}
WORDS_BY_RULE: dict[str, list[dict[str, Any]]] = {}
for word in WORDS:
    WORDS_BY_RULE.setdefault(word["rule_id"], []).append(word)


def scope_id_for(mode: str, rule_id: str | None = None, rule_ids: list[str] | None = None) -> str:
    if mode in {"word_nn", "rule"} and (rule_ids or rule_id):
        selected = rule_ids or [str(rule_id)]
        digest = hashlib.sha1("|".join(sorted(selected)).encode("utf-8")).hexdigest()[:16]
        return f"word_nn:rules:{digest}"
    if mode == "errors":
        return "errors:bank"
    return mode


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
    unique = {word["id"]: word for word in pool}
    with db() as con:
        due_rows = con.execute(
            "SELECT word_id FROM word_progress WHERE user_id=? AND scope_id=? AND due_reviews>0 ORDER BY due_reviews DESC,last_seen_at",
            (user_id, "ege15:errors:bank"),
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
        "kind": "ege15_word",
        "source_word_id": word["id"],
        "prompt": word["variant"],
        "choices": list(SPELLING_TYPES),
        "category": word["category"],
        "rule_id": word["rule_id"],
        "rule_name": word["rule_name"],
        "explanation": word["explanation"],
        "correct_spelling": word["correct_spelling"],
        "_correct_answer": word["answer"],
    }


def combined_sentence(items: list[dict[str, Any]]) -> str:
    sentence = items[0]["context"]
    for item in items[1:]:
        label = item.get("gap_label") or ""
        spelling = item.get("correct_spelling") or ""
        if label and spelling and spelling in sentence:
            sentence = sentence.replace(spelling, label, 1)
    return sentence


def sentence_parts(sentence: str, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    targets = []
    for item in items:
        label = item.get("gap_label") or item["variant"]
        index = sentence.find(label)
        if index >= 0:
            targets.append((index, label, item))
    targets.sort(key=lambda value: value[0])
    parts: list[dict[str, Any]] = []
    cursor = 0
    for index, label, item in targets:
        if index < cursor:
            continue
        if index > cursor:
            parts.append({"text": sentence[cursor:index]})
        parts.append({"target": {"id": item["id"], "label": label}})
        cursor = index + len(label)
    if cursor < len(sentence):
        parts.append({"text": sentence[cursor:]})
    return parts


def sentence_question(group: dict[str, Any]) -> dict[str, Any]:
    items = group["items"]
    sentence = combined_sentence(items)
    return {
        "question_id": secrets.token_hex(8),
        "kind": "ege15_sentence",
        "prompt": "Укажите Н или НН для каждого слова с пропуском.",
        "parts": sentence_parts(sentence, items),
        "choices": list(SPELLING_TYPES),
        "category": "Предложение",
        "rule_id": "ege15_sentence",
        "rule_name": "Формат ЕГЭ",
        "explanation": "; ".join(item["explanation"] for item in items),
        "correct_spelling": "; ".join(item["correct_spelling"] for item in items),
        "_correct_answer": {item["id"]: item["answer"] for item in items},
        "_sentence_items": [item["id"] for item in items],
    }


def error_bank_words(user_id: str) -> list[dict[str, Any]]:
    with db() as con:
        rows = con.execute(
            "SELECT word_id FROM word_progress WHERE user_id=? AND scope_id=? AND due_reviews>0 ORDER BY due_reviews DESC,last_seen_at",
            (user_id, "ege15:errors:bank"),
        ).fetchall()
    return [WORD_BY_ID[row["word_id"]] for row in rows if row["word_id"] in WORD_BY_ID]


def start_practice(user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    mode = str(payload.get("mode") or "word_nn")
    count = max(1, min(int(payload.get("count") or 10), 30))
    if mode == "word_nn":
        rule_ids = [str(value) for value in payload.get("rule_ids") or [] if str(value) in WORDS_BY_RULE]
        pool = [word for rule_id in dict.fromkeys(rule_ids) for word in WORDS_BY_RULE[rule_id]]
        if not pool:
            raise ValueError("Выберите хотя бы одну часть речи.")
        scope = scope_id_for(mode, rule_ids=rule_ids)
        questions = [word_question(word) for word in pick_words(user["user_id"], scope, pool, min(count, len(pool)))]
    elif mode == "sentence_nn":
        scope = scope_id_for(mode)
        questions = [sentence_question(group) for group in random.sample(SENTENCES, min(count, len(SENTENCES)))]
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
        if "_sentence_items" in item:
            item["sentence_items"] = item.pop("_sentence_items")
        private[item["question_id"]] = item
        public.append({key: value for key, value in item.items() if key not in {"correct_answer", "sentence_items"}})
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
    if question["kind"] == "ege15_sentence":
        given = {str(key): normalize_answer(value) for key, value in (raw or {}).items()} if isinstance(raw, dict) else {}
        correct = question["correct_answer"]
        is_correct = all(given.get(item_id) == answer for item_id, answer in correct.items())
        for item_id, answer in correct.items():
            item_correct = given.get(item_id) == answer
            update_progress(con, user_id, "ege15:errors:bank", item_id, item_correct)
            if not item_correct:
                insert_attempt(con, user_id, session, question, question_id, given.get(item_id) or "—", answer, False, item_id, elapsed, ":sentence_word")
        display_given = ", ".join(f"{WORD_BY_ID[item_id]['gap_label']}: {given.get(item_id) or '—'}" for item_id in question["sentence_items"])
        display_correct = ", ".join(f"{WORD_BY_ID[item_id]['gap_label']}: {correct[item_id]}" for item_id in question["sentence_items"])
        insert_attempt(con, user_id, session, question, question_id, display_given, display_correct, is_correct, None, elapsed)
        return {
            "question_id": question_id,
            "is_correct": bool(is_correct),
            "given_answer": display_given,
            "correct_answer": display_correct,
            "explanation": question.get("explanation"),
            "correct_spelling": question.get("correct_spelling"),
        }
    given = normalize_answer(raw)
    correct = question["correct_answer"]
    is_correct = given == correct
    word_id = question.get("source_word_id")
    if word_id:
        update_progress(con, user_id, session["scope_id"], word_id, is_correct)
        if session["scope_id"] != "ege15:errors:bank":
            update_progress(con, user_id, "ege15:errors:bank", word_id, is_correct)
    insert_attempt(con, user_id, session, question, question_id, given or "—", correct, is_correct, word_id, elapsed)
    return {
        "question_id": question_id,
        "is_correct": bool(is_correct),
        "given_answer": given,
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
    raise ValueError("Для задания 15 ответы проверяются после завершения тренировки.")


def build_test_file(user: dict[str, Any], payload: dict[str, Any]) -> tuple[bytes, str, str]:
    if user.get("role") != "teacher":
        raise PermissionError("Функция доступна только учителю.")
    count = max(1, min(int(payload.get("count") or 10), 60))
    mode = str(payload.get("mode") or "sentence_nn")
    lines = ["ЕГЭ. Задание 15", ""]
    answers = ["", "Ответы", ""]
    if mode == "sentence_nn":
        for index, group in enumerate(random.sample(SENTENCES, min(count, len(SENTENCES))), 1):
            question = sentence_question(group)
            text = "".join(part.get("text", part.get("target", {}).get("label", "")) for part in question["parts"])
            lines.append(f"{index}. {text}")
            answers.append(f"{index}. " + ", ".join(f"{WORD_BY_ID[item_id]['gap_label']} — {question['_correct_answer'][item_id]}" for item_id in question["_sentence_items"]))
    else:
        rule_ids = [str(value) for value in payload.get("rule_ids") or [] if str(value) in WORDS_BY_RULE]
        pool = [word for rule_id in dict.fromkeys(rule_ids) for word in WORDS_BY_RULE[rule_id]]
        if not pool:
            raise ValueError("Нет слов для составления теста.")
        random.shuffle(pool)
        for index, word in enumerate(pool[:count], 1):
            lines.append(f"{index}. {word['variant']}")
            answers.append(f"{index}. {word['correct_spelling']} — {word['answer']}")
    return ("\n".join(lines + answers) + "\n").encode("utf-8"), "ege15_test.txt", "text/plain; charset=utf-8"
