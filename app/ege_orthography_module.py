from __future__ import annotations

import secrets
from typing import Any

import ege10_module
import ege11_module
import ege12_module
import ege13_module
import ege14_module
import ege15_module


PRACTICE_SESSIONS: dict[str, dict[str, Any]] = {}
EGE9_HANDLER: Any = None

TASKS: dict[str, dict[str, Any]] = {
    "ege9": {"title": "Задание 9", "mode": "line"},
    "ege10": {"title": "Задание 10", "mode": "line"},
    "ege11": {"title": "Задание 11", "mode": "line"},
    "ege12": {"title": "Задание 12", "mode": "line"},
    "ege13": {"title": "Задание 13", "mode": "line_ne"},
    "ege14": {"title": "Задание 14", "mode": "exam"},
    "ege15": {"title": "Задание 15", "mode": "sentence_nn"},
}


def set_ege9_handler(handler: Any) -> None:
    global EGE9_HANDLER
    EGE9_HANDLER = handler


def _module_for(activity: str) -> Any:
    if activity == "ege9":
        if EGE9_HANDLER is None:
            raise ValueError("Задание 9 ещё не подключено к сборному модулю.")
        return EGE9_HANDLER
    if activity == "ege10":
        return ege10_module
    if activity == "ege11":
        return ege11_module
    if activity == "ege12":
        return ege12_module
    if activity == "ege13":
        return ege13_module
    if activity == "ege14":
        return ege14_module
    if activity == "ege15":
        return ege15_module
    raise ValueError("Неизвестное задание орфографии.")


def task_counts_from_payload(payload: dict[str, Any]) -> dict[str, int]:
    raw = payload.get("task_counts") or payload.get("tasks") or {}
    counts: dict[str, int] = {}
    if isinstance(raw, dict):
        for activity, value in raw.items():
            if activity in TASKS:
                count = max(0, min(int(value or 0), 30))
                if count:
                    counts[activity] = count
    if not counts:
        activity = str(payload.get("activity") or "ege13")
        if activity in TASKS:
            counts[activity] = max(1, min(int(payload.get("count") or 1), 30))
    if not counts:
        raise ValueError("Выберите хотя бы одно задание и количество вопросов.")
    return counts


def start_practice(user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    task_counts = task_counts_from_payload(payload)
    aggregate_id = secrets.token_hex(12)
    sub_sessions: dict[str, dict[str, Any]] = {}
    public_questions: list[dict[str, Any]] = []
    for activity, count in task_counts.items():
        config = TASKS[activity]
        module = _module_for(activity)
        data = module.start_practice(user, {"mode": config["mode"], "count": count})
        sub_sessions[activity] = {
            "session_id": data["session_id"],
            "question_ids": [],
        }
        for question in data.get("questions") or []:
            original_id = question["question_id"]
            public_id = f"{activity}:{original_id}"
            question = dict(question)
            question["question_id"] = public_id
            question["orthography_activity"] = activity
            question["rule_name"] = f"{config['title']}: {question.get('rule_name') or ''}".strip()
            sub_sessions[activity]["question_ids"].append((public_id, original_id))
            public_questions.append(question)
    PRACTICE_SESSIONS[aggregate_id] = {"user_id": user["user_id"], "sub_sessions": sub_sessions}
    return {"session_id": aggregate_id, "questions": public_questions}


def submit_practice(user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    session_id = str(payload.get("session_id") or "")
    session = PRACTICE_SESSIONS.get(session_id)
    if not session or session["user_id"] != user["user_id"]:
        raise ValueError("Сессия тренировки не найдена.")
    answers = payload.get("answers") or {}
    merged_results: list[dict[str, Any]] = []
    for activity, sub in session["sub_sessions"].items():
        sub_answers = {
            original_id: answers.get(public_id)
            for public_id, original_id in sub["question_ids"]
        }
        result = _module_for(activity).submit_practice(
            user,
            {
                "session_id": sub["session_id"],
                "answers": sub_answers,
                "time_spent_sec": payload.get("time_spent_sec"),
            },
        )
        for item in result.get("results") or []:
            item = dict(item)
            item["activity"] = activity
            item["activity_title"] = TASKS[activity]["title"]
            merged_results.append(item)
    PRACTICE_SESSIONS.pop(session_id, None)
    return {
        "results": merged_results,
        "correct": sum(result["is_correct"] for result in merged_results),
        "total": len(merged_results),
    }


def check_practice_answer(user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    raise ValueError("Сборная орфография проверяется после завершения тренировки.")


def build_test_file(user: dict[str, Any], payload: dict[str, Any]) -> tuple[bytes, str, str]:
    if user.get("role") != "teacher":
        raise PermissionError("Функция доступна только учителю.")
    task_counts = task_counts_from_payload(payload)
    parts: list[str] = ["Орфография. Режимы ЕГЭ", ""]
    for activity, count in task_counts.items():
        module = _module_for(activity)
        body, _, _ = module.build_test_file(
            user,
            {
                **payload,
                "activity": activity,
                "mode": TASKS[activity]["mode"],
                "count": count,
            },
        )
        parts.append(body.decode("utf-8", errors="replace").strip())
        parts.append("")
    return ("\n".join(parts).strip() + "\n").encode("utf-8"), "orthography_ege_test.txt", "text/plain; charset=utf-8"
