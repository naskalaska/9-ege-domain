"""Shared, retry-safe sessions for speech trainers; answer keys stay on the server."""
import random
import secrets
import threading
import time
from pathlib import Path
import sqlite3
import ege1_3_module as lab
from attempt_content import describe_question

DB_PATH = Path(__file__).resolve().parents[1] / 'data' / 'ege_app.db'
LOCK = threading.RLock()

class Trainer:
    def __init__(self, slug, words, modes, maker):
        self.slug, self.WORDS, self.modes, self.maker = slug, words, modes, maker
        self.WORD_BY_ID = {w['id']:w for w in words}
        self.WORDS_BY_RULE = {}
        for w in words:
            self.WORDS_BY_RULE.setdefault(w['rule_id'], []).append(w)
        self.RULES = [dict(rule_id=k, category=v[0]['category'], rule_name=v[0]['rule_name'], count=len(v)) for k,v in self.WORDS_BY_RULE.items()]
        self.PRACTICE_SESSIONS = {}

    def scope_id_for(self, mode, rule_id=None, rule_ids=None):
        return f'{self.slug}:{mode}' + (':bank' if mode == 'errors' else '')

    def db(self):
        con = sqlite3.connect(DB_PATH)
        con.row_factory = sqlite3.Row
        return con

    def word_question(self, word):
        q = self.maker(word, 'truth' if self.slug=='ege7' and not word.get('incorrect_variant') else next(iter(self.modes)))
        q['_correct_answer'] = q.pop('correct_answer')
        return q

    def public_question(self, q):
        return {k:v for k,v in q.items() if not k.startswith('_') and k not in {'correct_answer','explanation','source_word_id','source_word_ids'}}

    def select_questions(self, user, payload, teacher=False):
        mode = str(payload.get('mode') or next(iter(self.modes)))
        if mode not in self.modes and mode != 'errors':
            raise ValueError('Неизвестный режим тренировки.')
        count = max(1, min(int(payload.get('count') or 10), 60 if teacher else 30))
        selected = set(payload.get('rule_ids') or [])
        if selected - self.WORDS_BY_RULE.keys():
            raise ValueError('Неизвестный вид ошибки.')
        pool = [w for w in self.WORDS if not selected or w['rule_id'] in selected]
        if self.slug=='ege7' and mode in {'fix','choice'}:
            pool=[w for w in pool if w.get('training_enabled') and w.get('incorrect_variant')]
        error_ids=set()
        if mode == 'errors' or payload.get('include_errors'):
            with self.db() as con:
                if teacher:
                    rows = con.execute("SELECT DISTINCT wp.word_id FROM word_progress wp JOIN users u ON u.user_id=wp.user_id WHERE u.teacher_id=? AND wp.scope_id=? AND wp.due_reviews>0", (user['user_id'],self.scope_id_for('errors')))
                else:
                    rows = con.execute('SELECT word_id FROM word_progress WHERE user_id=? AND scope_id=? AND due_reviews>0', (user['user_id'],self.scope_id_for('errors')))
                error_ids = {r[0] for r in rows}
            if mode == 'errors':
                pool = [w for w in pool if w['id'] in error_ids]
        if not pool:
            raise ValueError('В копилке пока нет ошибок.' if mode == 'errors' else 'База готовится к проверке. Автоматическая тренировка пока недоступна.')
        if mode == 'exam' and self.slug!='ege6':
            return [self.maker(None, mode, pool) for _ in range(count)]
        errors=[w for w in pool if w['id'] in error_ids]
        rest=[w for w in pool if w['id'] not in error_ids]
        random.shuffle(errors);random.shuffle(rest)
        return [self.maker(w, ('fix' if w.get('incorrect_variant') else 'truth') if mode=='errors' and self.slug=='ege7' else next(iter(self.modes)) if mode == 'errors' else mode) for w in (errors+rest)[:count]]

    def start_practice(self, user, payload):
        questions = self.select_questions(user,payload)
        sid = secrets.token_hex(12)
        mode = str(payload.get('mode') or next(iter(self.modes)))
        with LOCK:
            self.PRACTICE_SESSIONS = {k:v for k,v in self.PRACTICE_SESSIONS.items() if time.time()-v['created_at']<86400}
            if len(self.PRACTICE_SESSIONS)>=500:
                self.PRACTICE_SESSIONS.pop(next(iter(self.PRACTICE_SESSIONS)))
            self.PRACTICE_SESSIONS[sid] = dict(user_id=user['user_id'],mode=mode,scope_id=self.scope_id_for(mode),questions={q['question_id']:q for q in questions},results={},created_at=time.time())
        return dict(session_id=sid,mode=mode,questions=[self.public_question(q) for q in questions])

    def answer_complete(self,q,a):
        if q['kind']=='speech_truth':
            return isinstance(a,dict) and (a.get('verdict')=='true' or (a.get('verdict')=='false' and isinstance(a.get('word'),str) and bool(a['word'].strip())))
        if q['kind']=='speech_match':
            return isinstance(a,dict) and set(a)==set(q['correct_answer']) and all(isinstance(v,str) and v in {str(i+1) for i in range(len(q['sentences']))} for v in a.values()) and len(set(a.values()))==len(a)
        if q['kind']=='speech_choice':
            return isinstance(a,str) and a in {c['value'] for c in q['choices']}
        if q['kind']=='speech_stress':
            return isinstance(a,str) and a.isdigit() and int(a)<len(q['prompt']) and q['prompt'][int(a)] in 'аеёиоуыэюя'
        if q['kind']=='speech_multi':
            return isinstance(a,str) and bool(a) and all(c in '12345' for c in a)
        return isinstance(a,str) and bool(a.strip())

    def grade(self,q,a):
        key=q.get('correct_answer',q.get('_correct_answer'))
        if q['kind']=='speech_truth':
            ok=a['verdict']==key['verdict'] and (key['verdict']=='true' or lab.normalize_text(a['word'])==lab.normalize_text(key['word']))
            return ok,('Правильно' if a['verdict']=='true' else 'Неправильно: '+a['word']),('Правильно' if key['verdict']=='true' else 'Неправильно: '+key['word'])
        if q['kind']=='speech_stress':
            index=int(a)
            return a==str(key),q['prompt'][:index]+q['prompt'][index].upper()+q['prompt'][index+1:]+' '+q.get('context',''),q.get('_norm_form',str(key))+' '+q.get('context','')
        if q['kind']=='speech_match':
            given='; '.join(f'{k}–{a[k]}' for k in sorted(a))
            correct='; '.join(f'{k}–{key[k]}' for k in sorted(key))
            return a==key,given,correct
        if isinstance(key,list):
            return lab.normalize_text(a) in {lab.normalize_text(k) for k in key},a,'; '.join(key)
        if q['kind']=='speech_multi':
            return ''.join(sorted(set(a)))==key,a,key
        labels={'true':'Верно','false':'Неверно'}
        return a==str(key),labels.get(a,a),labels.get(str(key),str(key))

    def record_attempt(self,con,user_id,session,qid,q,answer,elapsed=None):
        if not self.answer_complete(q,answer):
            raise ValueError('Ответьте на все задания перед проверкой.')
        ok,given,key=self.grade(q,answer)
        bad_words=[]
        for wid in q.get('source_word_ids',[q['source_word_id']]):
            item_ok=ok
            check=q.get('_word_checks',{}).get(wid)
            if check and q['kind']=='speech_multi':
                item_ok=(check['index'] in answer)==check['correct']
            elif check and q['kind']=='speech_match':
                actual=next((k for k,v in answer.items() if v==check['index']),None)
                item_ok=actual==check['type']
            if not item_ok:bad_words.append(wid)
            for scope in {session['scope_id'],self.scope_id_for('errors')}:
                lab.update_progress(con,user_id,scope,wid,item_ok)
        attempt_word=bad_words[0] if bad_words else q['source_word_id']
        topic=self.WORD_BY_ID.get(attempt_word,q)
        con.execute("INSERT INTO attempts(attempt_id,user_id,mode,scope_id,word_id,rule_id,category,rule_name,question_id,prompt,given_answer,correct_answer,is_correct,created_at,time_spent_sec) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(secrets.token_hex(12),user_id,session['mode'],session['scope_id'],attempt_word,topic['rule_id'],topic['category'],topic['rule_name'],qid,describe_question(q),given,key,int(ok),lab.now_iso(),elapsed))
        return dict(question_id=qid,is_correct=ok,given_answer=given,correct_answer=key,explanation=q.get('explanation',''))

    def submit_practice(self,user,payload):
        with LOCK:
            session=self.PRACTICE_SESSIONS.get(str(payload.get('session_id') or ''))
            if not session or session['user_id']!=user['user_id']:
                raise ValueError('Сессия тренировки не найдена.')
            answers=payload.get('answers') or {}
            if not isinstance(answers,dict):raise ValueError('Некорректные ответы.')
            pending={k:q for k,q in session['questions'].items() if k not in session['results']}
            if any(not self.answer_complete(q,answers.get(k)) for k,q in pending.items()):
                raise ValueError('Ответьте на все задания перед проверкой.')
            with self.db() as con:
                con.execute('BEGIN IMMEDIATE')
                results={k:self.record_attempt(con,user['user_id'],session,k,q,answers[k],payload.get('time_spent_sec')) for k,q in pending.items()}
            session['results'].update(results)
            rows=list(session['results'].values())
            return dict(results=rows,correct=sum(r['is_correct'] for r in rows),total=len(rows))

    def check_practice_answer(self,user,payload):
        with LOCK:
            session=self.PRACTICE_SESSIONS.get(str(payload.get('session_id') or ''))
            if not session or session['user_id']!=user['user_id']:
                raise ValueError('Сессия тренировки не найдена.')
            qid=str(payload.get('question_id') or '')
            if qid not in session['questions']:
                raise ValueError('Вопрос не найден в этой тренировке.')
            if qid in session['results']:
                return session['results'][qid]
            with self.db() as con:
                con.execute('BEGIN IMMEDIATE')
                result=self.record_attempt(con,user['user_id'],session,qid,session['questions'][qid],payload.get('answer'),payload.get('time_spent_sec'))
            session['results'][qid]=result
            return result

    def build_test_file(self,user,payload):
        if user.get('role')!='teacher':
            raise PermissionError('Функция доступна только учителю.')
        questions=self.select_questions(user,payload,teacher=True)
        lines=[f'ЕГЭ. {self.slug}', '']
        keys=[]
        for i,q in enumerate(questions,1):
            lines.extend([f'{i}. '+describe_question(q),''])
            keys.append(f'{i}. '+self.grade(q,q['correct_answer'][0] if isinstance(q['correct_answer'],list) else q['correct_answer'])[2])
        return ('\n'.join(lines+['Ответы']+keys)+'\n').encode(),self.slug+'-test.txt','text/plain; charset=utf-8'
