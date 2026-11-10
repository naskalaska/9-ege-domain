"""Load the supplied banks without changing source keys or editorial status."""
import json
import random
import re
import secrets
from pathlib import Path
from ege_speech_engine import Trainer

ROOT=Path(__file__).resolve().parents[1]

def load(name):
    return json.loads((ROOT/name).read_text(encoding='utf-8'))

def base(w,kind,prompt,key,**extra):
    return dict(question_id=secrets.token_hex(12),kind=kind,prompt=prompt,correct_answer=key,
        source_word_id=w['id'],rule_id=w['rule_id'],rule_name=w['rule_name'],category=w['category'],
        explanation=w.get('explanation',''),**extra)

stress_bank=load('task_4_orthoepy_database_context.json')
stress_words=[]
for raw in stress_bank['words']:
    if raw.get('human_review_required'):
        continue
    w=dict(raw,id=raw['id'],rule_id='stress:'+str(raw.get('part_of_speech') or 'other'),
        rule_name=raw.get('part_of_speech') or 'Ударение',category='Орфоэпия',
        explanation=(raw['explanation'].get('short') if isinstance(raw.get('explanation'),dict) else raw.get('explanation')) or raw.get('learning_note') or raw['correct'])
    stress_words.append(w)
wrong_by_word={}
for row in stress_bank['incorrect']:
    wrong_by_word.setdefault(row['word_id'],[]).append(row.get('exam_display') or row['display'])

def context(w):
    return (w.get('training_context') or {}).get('display','') if (w.get('training_context') or {}).get('required') else ''

def displayed(w):
    wrong=wrong_by_word.get(w['id'],[])
    valid=not wrong or random.choice([True,False])
    return (w.get('exam_correct') or w['correct']) if valid else random.choice(wrong),valid

def stress_question(w,mode,pool=None):
    if mode=='exam':
        pool=[r for r in pool if r.get('ege_2026_eligible')]
        wrong_count=random.randint(1,3)
        wrong_pool=[r for r in pool if wrong_by_word.get(r['id'])]
        wrong_rows=random.sample(wrong_pool,wrong_count)
        rows=wrong_rows+random.sample([r for r in pool if r not in wrong_rows],5-wrong_count)
        random.shuffle(rows)
        wrong_ids={r['id'] for r in wrong_rows}
        options=[(random.choice(wrong_by_word[r['id']]),False) if r['id'] in wrong_ids else (r.get('exam_correct') or r['correct'],True) for r in rows]
        q=base(rows[0],'speech_multi','Укажите номера слов, в которых верно выделена ударная гласная.', ''.join(str(i+1) for i,(_,ok) in enumerate(options) if ok),
            rows=[text+' '+context(row) for row,(text,_) in zip(rows,options)],source_word_ids=[r['id'] for r in rows])
        q['_word_checks']={r['id']:{'index':str(i+1),'correct':options[i][1]} for i,r in enumerate(rows)}
        q['explanation']='; '.join(r['correct']+' '+context(r) for r in rows)
        return q
    if mode=='truth':
        text,ok=displayed(w)
        return base(w,'speech_choice',text+' '+context(w),'true' if ok else 'false',instruction='Верно ли поставлено ударение?',choices=[{'value':'true','label':'Верно'},{'value':'false','label':'Неверно'}])
    raw=w['RAW'].lower().replace('ё','е')
    return base(w,'speech_stress',raw,str(w['stress']['char_index']),context=context(w),instruction='Выделите ударную гласную.',_norm_form=w['correct'])

ege4=Trainer('ege4',stress_words,{'stress':None,'truth':None,'exam':None},stress_question)

raw6=load('ege6_methodical_database.json')
words6=[]
for r in raw6['entries']:
    accepted=list(dict.fromkeys(r['answer']['accepted']))
    rule=r['methodology']['error_category']
    words6.append(dict(id=r['id'],rule_id='lex:'+rule,rule_name=raw6['tag_dictionary'][rule],category='Лексические нормы',
        sentence=r['task']['sentence'],instruction=re.sub(r'^\d+\.\s*','',r['task']['instruction']),accepted=accepted,explanation=r['methodical_revision']['explanation']))
def lexical_question(w,mode,pool=None):
    if w is None:
        w=random.choice(pool)
    return base(w,'speech_input',w['sentence'],w['accepted'],instruction=w['instruction'])
ege6=Trainer('ege6',words6,{'rule':None,'exam':None},lexical_question)

raw8=load('task_8_by_norm.json')
words8=[]
labels8={}
for norm,groups in raw8['norms'].items():
    for group,rows in groups.items():
        if not isinstance(rows,list):
            continue
        for r in rows:
            name=r.get('error_type_name') or next((x.get('error_type_name') for x in groups.get('incorrect',[]) if x.get('error_type_name')),norm)
            labels8[norm]=name
            words8.append(dict(id=f"ru8:{r['card_id']}:{r['sentence_number']}:{norm}",rule_id=norm,rule_name=name,
                category='Грамматические нормы',sentence=r['sentence_text'],is_correct=r['is_correct'],
                explanation=r.get('case_explanation') or r.get('rule_explanation') or 'Норма соблюдена.'))

def grammar_question(w,mode,pool=None):
    if mode=='exam':
        by_rule={}
        for row in pool:
            if not row['is_correct']:
                by_rule.setdefault(row['rule_id'],[]).append(row)
        if len(by_rule)<5:
            raise ValueError('Для формата ЕГЭ нужно пять допущенных видов ошибок.')
        rules=random.sample(list(by_rule),5)
        selected=[random.choice(by_rule[r]) for r in rules]
        distractors=[r for r in pool if r['is_correct'] and r['sentence'] not in {s['sentence'] for s in selected}]
        unique={r['sentence']:r for r in distractors}
        selected+=random.sample(list(unique.values()),min(4,len(unique)))
        random.shuffle(selected)
        key={chr(1040+i):str(next(j for j,r in enumerate(selected) if r['rule_id']==rule and not r['is_correct'])+1) for i,rule in enumerate(rules)}
        q=base(selected[0],'speech_match','Соедините каждый тип ошибки с предложением.',key,
            types=[{'id':chr(1040+i),'label':labels8[r]} for i,r in enumerate(rules)],sentences=[r['sentence'] for r in selected],source_word_ids=[r['id'] for r in selected])
        q['_word_checks']={r['id']:{'index':str(i+1),'type':next((k for k,v in key.items() if v==str(i+1)),None)} for i,r in enumerate(selected)}
        q['explanation']='\n'.join(r['explanation'] for r in selected if not r['is_correct'])
        return q
    if mode in {'truth','rule'}:
        return base(w,'speech_choice',w['sentence'],'true' if w['is_correct'] else 'false',instruction='Соблюдена ли грамматическая норма?',choices=[{'value':'true','label':'Верно'},{'value':'false','label':'Неверно'}])
    return base(w,'speech_choice',w['sentence'],'none' if w['is_correct'] else w['rule_id'],instruction='Определите тип ошибки.',choices=[{'value':k,'label':v} for k,v in labels8.items()]+[{'value':'none','label':'Ошибки нет'}])

ege8=Trainer('ege8',words8,{'rule':None,'truth':None,'classify':None,'exam':None},grammar_question)


raw7=load('task_7_database_statuses_final_norm.json')
words7=[]
for r in raw7['phrase_pairs']:
    pos=r['part_of_speech'].lower().removeprefix('имя ').split('/')[0].split('(')[0].strip()
    pos=pos.removeprefix('отглагольное ').capitalize()
    words7.append(dict(r, rule_id='morph:'+pos,
        rule_name=pos,category=pos,
        explanation=r['rule_explanation']))
words7.sort(key=lambda w:(w['rule_name'],w['id']))

def morphology_question(w,mode,pool=None):
    if mode=='exam':
        errors=[r for r in pool if r.get('incorrect_variant') and r.get('training_enabled')]
        if not errors: raise ValueError('В выбранной части речи нет ошибочных форм для ЕГЭ.')
        w=random.choice(errors)
        others={r['correct_variant'].casefold():r for r in words7 if r['id']!=w['id'] and r['correct_variant'].casefold()!=w['correct_variant'].casefold()}
        if len(others)<4: raise ValueError('Для ЕГЭ выберите части речи с пятью разными сочетаниями.')
        rows=[(w,False)]+[(r,True) for r in random.sample(list(others.values()),4)]
        random.shuffle(rows)
        return base(w,'speech_input','\n'.join(f"{i+1}) {r['correct_variant'] if ok else r['incorrect_variant']}" for i,(r,ok) in enumerate(rows)),
            [w['highlighted_correct_form']],instruction='В одном из пяти сочетаний допущена ошибка. Запишите исправленное слово.')
    wrong=w.get('incorrect_variant') if w.get('training_enabled') else None
    if mode=='truth':
        ok=not wrong or random.choice([True,False])
        return base(w,'speech_truth',w['correct_variant'] if ok else wrong,
            dict(verdict='true' if ok else 'false',word=w['highlighted_correct_form']),
            instruction='Правильно или неправильно? Если неправильно, впишите исправленное слово.')
    if mode=='choice':
        variants=[w['correct_variant']]
        if wrong: variants.append(wrong)
        else: raise ValueError('Для выбора пары нужна ошибочная форма этого же сочетания.')
        random.shuffle(variants)
        return base(w,'speech_choice','Как правильно?',w['correct_variant'],choices=[dict(value=s,label=s) for s in variants])
    if not wrong: raise ValueError('Для режима исправления нужна ошибочная форма.')
    return base(w,'speech_input',wrong,[w['highlighted_correct_form']],
        instruction='Исправьте ошибочную форму. Запишите исправленное слово.')

ege7=Trainer('ege7',words7,{'fix':None,'truth':None,'choice':None,'exam':None},morphology_question)
