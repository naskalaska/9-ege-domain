"""Keep positional answer keys varied without changing the spelling content."""
import random
import re


def vary_row_answers(questions):
    previous = None
    for question in questions:
        key = question.get('_correct_answer')
        rows = question.get('rows')
        if not isinstance(key,str) or not rows or not re.fullmatch(r'[1-5]+',key):
            continue
        if key == previous and 0 < len(key) < len(rows):
            order = list(range(len(rows)))
            for _ in range(50):
                random.shuffle(order)
                changed = ''.join(str(i+1) for i,old in enumerate(order) if str(old+1) in key)
                if changed != key:
                    break
            for field in ('rows','row_word_ids','_line_rows','_line_items','_exam_rows'):
                if field in question:
                    question[field] = [question[field][old] for old in order]
            question['_correct_answer'] = changed
            question['explanation'] = re.sub(r'Правильные строки: [\d, ]+\.?',
                'Правильные строки: '+', '.join(changed)+'.',question.get('explanation',''))
            key = changed
        previous = key
