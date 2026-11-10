"""Persist the actual exercise, including rows, rather than just its instruction."""


def describe_question(question):
    prompt = question.get('prompt') or ''
    if str(question.get('kind', '')).startswith('text_lab_'):
        import re
        text = '\n\n'.join(re.sub(r'\s*\n\s*', ' ', p).strip()
                             for p in re.split(r'\n\s*\n', question.get('text') or '') if p.strip())
        parts = [text, prompt]
        if question.get('statement'):
            parts.append(question['statement'])
        parts.extend(f"{o['n']}) {o['text']}" for o in question.get('options') or [])
        return '\n\n'.join(parts)
    if question.get('kind') == 'speech_match':
        return prompt+'\n'+'\n'.join(f"{t['id']}) {t['label']}" for t in question['types'])+'\n'+'\n'.join(f"{i+1}) {t}" for i,t in enumerate(question['sentences']))
    if question.get('kind') in {'speech_choice','speech_stress','speech_input','speech_truth'}:
        text=(question.get('instruction') or '')+'\n'+prompt+' '+question.get('context','')
        if question.get('choices'):
            text+='\n'+'\n'.join(f"{i}) {c['label']}" for i,c in enumerate(question['choices'],1))
        return text
    if question.get('rows'):
        lines = []
        for index,row in enumerate(question['rows'],1):
            text = ', '.join(str(w) for w in row) if isinstance(row,list) else row.get('sentence','') if isinstance(row,dict) else str(row)
            lines.append(f'{index}) {text}')
        return prompt+'\n'+'\n'.join(lines)
    if question.get('parts'):
        return prompt+'\n'+''.join(part.get('text',part.get('target',{}).get('label','')) for part in question['parts'])
    return prompt
