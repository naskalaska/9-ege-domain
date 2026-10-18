"""Persist the actual exercise, including rows, rather than just its instruction."""


def describe_question(question):
    prompt = question.get('prompt') or ''
    if question.get('rows'):
        lines = []
        for index,row in enumerate(question['rows'],1):
            text = ', '.join(str(w) for w in row) if isinstance(row,list) else row.get('sentence','') if isinstance(row,dict) else str(row)
            lines.append(f'{index}) {text}')
        return prompt+'\n'+'\n'.join(lines)
    if question.get('parts'):
        return prompt+'\n'+''.join(part.get('text',part.get('target',{}).get('label','')) for part in question['parts'])
    return prompt
