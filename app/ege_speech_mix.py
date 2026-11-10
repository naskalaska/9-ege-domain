from __future__ import annotations

import secrets
import threading
import time
from typing import Any

import ege1_3_module
import ege5_module
from ege_speech_module import ege4,ege6,ege7,ege8


PRACTICE_SESSIONS: dict[str, dict[str, Any]] = {}
SESSION_LOCK = threading.RLock()

TASKS = {**{f'ege{n}': {'title':f'Задание {n}', 'mode':'exam'} for n in (1,2,3,4,6,7,8)}, 'ege5':{'title':'Задание 5','mode':'paronym_exam'}}

def _module_for(activity):
    if activity in {'ege1','ege2','ege3'}:
        return TextTask(int(activity[-1]))
    if activity=='ege5':
        return ege5_module
    return {'ege4':ege4,'ege6':ege6,'ege7':ege7,'ege8':ege8}[activity]

class TextTask:
    def __init__(self,n): self.n=n
    def start_practice(self,user,payload):
        return ege1_3_module.start_practice(user,{**payload,'mode':'task_exam_'+str(self.n)})
    def submit_practice(self,user,payload): return ege1_3_module.submit_practice(user,payload)
    def check_practice_answer(self,user,payload): return ege1_3_module.check_practice_answer(user,payload)
    def build_test_file(self,user,payload): return ege1_3_module.build_test_file(user,{**payload,'mode':'task_exam_'+str(self.n)})


def task_counts_from_payload(payload: dict[str, Any]) -> dict[str, int]:
    raw = payload.get("task_counts") or payload.get("tasks") or {}
    counts: dict[str, int] = {}
    if isinstance(raw, dict):
        for activity, value in raw.items():
            if activity in TASKS:
                count = max(0, min(int(value or 0), 30))
                if count:
                    counts[activity] = count
    if not counts and not raw:
        activity = str(payload.get("activity") or "ege4")
        if activity in TASKS:
            counts[activity] = max(1, min(int(payload.get("count") or 1), 30))
    if not counts:
        raise ValueError("Выберите хотя бы одно задание и количество вопросов.")
    if counts.get('ege6') and not ege6.WORDS:
        raise ValueError('База задания 6 ожидает допуска к автоматической проверке.')
    return counts


def _start_practice(user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    task_counts = task_counts_from_payload(payload)
    expired=[k for k,v in PRACTICE_SESSIONS.items() if time.time()-v.get('created_at',0)>86400]
    for k in expired:PRACTICE_SESSIONS.pop(k,None)
    if len(PRACTICE_SESSIONS)>=500:PRACTICE_SESSIONS.pop(next(iter(PRACTICE_SESSIONS)))
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
    PRACTICE_SESSIONS[aggregate_id] = {"user_id": user["user_id"], "sub_sessions": sub_sessions, "questions": public_questions,"created_at":time.time()}
    return {"session_id": aggregate_id, "questions": public_questions,"created_at":time.time()}


def start_practice(user,payload):
    with SESSION_LOCK:
        return _start_practice(user,payload)


def _submit_practice(user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    session_id = str(payload.get("session_id") or "")
    session = PRACTICE_SESSIONS.get(session_id)
    if not session or session["user_id"] != user["user_id"]:
        raise ValueError("Сессия тренировки не найдена.")
    if session.get('result'):
        return session['result']
    answers = payload.get("answers") or {}
    from learning_module import answer_complete
    if not isinstance(answers,dict) or any(not answer_complete(q,answers.get(q['question_id'])) for q in session['questions']):
        raise ValueError('Ответьте на все задания перед проверкой.')
    merged_results: list[dict[str, Any]] = []
    for activity, sub in session["sub_sessions"].items():
        sub_answers = {
            original_id: answers.get(public_id)
            for public_id, original_id in sub["question_ids"]
        }
        checked=session.get('checked_results',{})
        if all(public in checked for public,original in sub['question_ids']):
            rows=[checked[public] for public,original in sub['question_ids']]
            sub['result']=dict(results=rows,correct=sum(r['is_correct'] for r in rows),total=len(rows))
        if 'result' in sub:
            result=sub['result']
        else:
            result = _module_for(activity).submit_practice(
                user,
                {
                    "session_id": sub["session_id"],
                    "answers": sub_answers,
                    "time_spent_sec": payload.get("time_spent_sec"),
                },
            )
            sub['result']=result
        original_to_public = {original:public for public,original in sub['question_ids']}
        for item in result.get("results") or []:
            item = dict(item)
            item["question_id"] = original_to_public.get(item["question_id"],item["question_id"])
            item["activity"] = activity
            item["activity_title"] = TASKS[activity]["title"]
            merged_results.append(item)
    session["result"] = {
        "results": merged_results,
        "correct": sum(result["is_correct"] for result in merged_results),
        "total": len(merged_results),
    }
    return session["result"]


def submit_practice(user,payload):
    with SESSION_LOCK:
        return _submit_practice(user,payload)


def check_practice_answer(user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    with SESSION_LOCK:
        session=PRACTICE_SESSIONS.get(str(payload.get('session_id') or ''))
        if not session or session['user_id']!=user['user_id']:
            raise ValueError('Сессия тренировки не найдена.')
        qid=str(payload.get('question_id') or '')
        activity,_,original=qid.partition(':')
        sub=session['sub_sessions'].get(activity)
        if not sub or (qid,original) not in sub['question_ids']:
            raise ValueError('Вопрос не найден в этой тренировке.')
        checked=session.setdefault('checked_results',{})
        if qid not in checked:
            result=_module_for(activity).check_practice_answer(user,{**payload,'session_id':sub['session_id'],'question_id':original})
            checked[qid]={**result,'question_id':qid,'activity':activity,'activity_title':TASKS[activity]['title']}
        return checked[qid]


def build_test_file(user: dict[str, Any], payload: dict[str, Any]) -> tuple[bytes, str, str]:
    if user.get("role") != "teacher":
        raise PermissionError("Функция доступна только учителю.")
    task_counts = task_counts_from_payload(payload)
    parts: list[str] = ["Культура речи", ""]
    for activity, count in task_counts.items():
        module = _module_for(activity)
        if activity == 'ege5':
            from server import build_ege5_test_file
            builder = build_ege5_test_file
        else:
            builder = module.build_test_file
        body, _, _ = builder(
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
    return ("\n".join(parts).strip() + "\n").encode("utf-8"), "speech_ege_test.txt", "text/plain; charset=utf-8"
