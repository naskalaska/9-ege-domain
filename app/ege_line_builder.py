"""Build rows by spelling family AND the alternatives at the gap, never by key alone."""
import random
import re
import secrets
from collections import defaultdict


def spelling_group(task, word):
    category, rule = word['category'], word['rule_name']
    letter = word['correct_letter']
    if letter not in 'аеёиоуыэюяьъзсдтчщк':
        return None
    before = re.split(r'\.{2,}|…', word['variant'].lower())[0][-1:]
    if task == 9:
        family = category
        if category == 'гласные после Ц':
            pair = 'иы'
        elif category == 'гласные после шипящих':
            pair = 'оё' if letter in 'оё' else 'иы' if letter == 'и' else 'ую'
        elif category == 'корни с чередованием':
            # ПЛЫВ is a third alternative, not an И/Ы spelling. Keep it in word practice.
            if letter == 'ы' or rule in {'им/ин // а/я', 'жим/жа'}:
                return None
            pair = 'ао' if letter in 'ао' else 'еи' if letter in 'еи' else None
        elif category == 'контекстные смысловые пары':
            if rule in {'разредить/разрядить', 'свет/свят: посвятить/посвящение/осветить/освещение/просвещение'}:
                pair = 'ея'
            elif rule == 'частота/чистота':
                pair = 'аи'
            elif rule == 'умалять/умолять/умиляться' and letter == 'и':
                return None
            else:
                pair = 'ао' if letter in 'ао' else 'еи'
        elif before and before in 'жшчщ':
            # Loan-word exceptions (брошюра, жюри) must not join ordinary root vowels.
            family += ' / после шипящих'
            pair = 'ую' if letter in 'ую' else 'иы' if letter in 'иы' else 'оё' if letter in 'оё' else 'еэ'
        elif before == 'ц':
            family += ' / после Ц'
            pair = 'иы' if letter in 'иы' else 'ео'
        else:
            pair = 'ао' if letter in 'ао' else 'еи' if letter in 'еи' else 'ея' if letter == 'я' else 'ую'
    elif task == 10:
        family = category
        pair = {'приставки ПРЕ/ПРИ':'еи', 'приставки на -з/-с':'зс',
                'И/Ы после приставок':'иы', 'ь/ъ':'ьъ'}.get(category)
        if pair is None:
            pair = 'ао' if letter in 'ао' else 'дт' if letter in 'дт' else 'еи'
    elif task == 11:
        family = category + ' / ' + rule
        if rule == 'ОВА-ЕВА-ЫВА-ИВА-ВА':
            pair = 'оы' if letter in 'оы' else 'еи' if letter in 'еи' else None
        elif rule == 'О-Ё-Е':
            pair = 'оё' if letter in 'оё' else None
        elif rule == 'ЧИК-ЩИК':
            pair = 'чщ'
        elif rule == 'Ы-И':
            pair = 'иы'
        elif rule in {'ОВ-ЕВ','ОВСТВ-ЕВСТВ','ОТ-ЕТ','ОСТЬ-ЕСТЬ','ЕНЬК-ОНЬК'}:
            pair = 'ео'
        elif rule == 'ЯН-ЕН-ЕНН-ИН':
            pair = 'ея' if letter in 'ея' else None
        else:
            pair = 'ао' if letter in 'ао' else 'еи' if letter in 'еи' else 'ая' if letter in 'ая' else None
    else:  # Task 12: distinguish the two conjugations at the same kind of ending.
        family = category + ' / ' + rule
        if category in {'Личные окончания глаголов','Суффиксы причастий настоящего времени'}:
            pair = 'еи' if letter in 'еи' else 'ау' if letter in 'ау' else 'яю' if letter in 'яю' else None
        else:
            pair = 'еи' if letter in 'еи' else 'ая' if letter in 'ая' else None
    return (family, pair) if pair and letter in pair else None


def make_question(task, words, source_words=None):
    row_size = 3 if task in {9,10} else 2
    pools = defaultdict(lambda: defaultdict(list))
    for word in words:
        group = spelling_group(task, word)
        if group:
            pools[group][word['correct_letter']].append(word)
    correct_groups = [g for g,pool in pools.items() if max(map(len,pool.values())) >= row_size]
    mixed_groups = [g for g,pool in pools.items() if len(pool) == 2 and sum(map(len,pool.values())) >= row_size]
    if len(set(correct_groups + mixed_groups)) < 5 or len(mixed_groups) < 3:
        raise ValueError(f'Недостаточно совместимых орфограмм для строк задания {task}.')
    focus = {w['id'] for w in source_words or []}
    focus_groups = {spelling_group(task,w) for w in source_words or []}
    # Fixed spellings (e.g. -ЧИВ-/-ЛИВ-) may form a correct row even when
    # their distractor has no correct examples in the bank. Never borrow words
    # from another family just to fabricate an incorrect row.
    correct_positions = set(random.sample(range(5), random.choice([2,3])))
    selected = []
    selected_categories = set()
    # Reserve mixed rows first; their pools are more constrained.
    for index in sorted(range(5),key=lambda i:i in correct_positions):
        candidates = [g for g in (correct_groups if index in correct_positions else mixed_groups)
                      if g not in [group for _,group in selected]]
        random.shuffle(candidates)
        def priority(group):
            category = next(iter(pools[group].values()))[0]['category']
            return (category in selected_categories, group not in focus_groups)
        candidates.sort(key=priority)
        group = candidates[0]
        selected.append((index,group))
        selected_categories.add(next(iter(pools[group].values()))[0]['category'])
    selected = [group for _,group in sorted(selected)]
    used_ids = set()
    rows = []
    for index,group in enumerate(selected):
        pool = pools[group]
        if index in correct_positions:
            letter = random.choice([l for l,ws in pool.items() if len(ws)>=row_size])
            pattern = [letter]*row_size
        else:
            first,second = list(pool)
            pattern = [first,second]
            if row_size == 3:
                pattern.append(random.choice([l for l,ws in pool.items() if len(ws)>=2]))
        picked = []
        for letter in pattern:
            fresh = [w for w in pool[letter] if w['id'] not in used_ids]
            preferred = [w for w in fresh if w['id'] in focus]
            word = random.choice(preferred or fresh)
            used_ids.add(word['id']);picked.append(word)
        random.shuffle(picked)
        rows.append({'words':picked,'is_correct':len({w['correct_letter'] for w in picked})==1,
                     'family':group[0],'alternatives':group[1]})
    random.shuffle(rows)
    correct = ''.join(str(i+1) for i,row in enumerate(rows) if row['is_correct'])
    return {'question_id':secrets.token_hex(8),'kind':'line',
            'prompt':f'Выберите все строки, где в {"трёх" if row_size == 3 else "обоих"} словах пропущена одна и та же буква.',
            'rows':[[w['variant'] for w in row['words']] for row in rows],
            'row_word_ids':[[w['id'] for w in row['words']] for row in rows],
            '_line_rows':[{'is_correct':row['is_correct'],'word_ids':[w['id'] for w in row['words']],
                           'family':row['family'],'alternatives':row['alternatives']} for row in rows],
            'choices':[str(i) for i in range(1,6)],'category':'Строка','rule_id':'line_same_letter',
            'rule_name':'Строки: разные орфограммы','address':'',
            'explanation':'В каждой строке — одна орфографическая группа и одна пара выбора букв. '
                          f'Правильные строки: {", ".join(correct)}.',
            'correct_spelling':'; '.join(', '.join(w['correct_spelling'] for w in row['words']) for row in rows),
            '_correct_answer':correct}
