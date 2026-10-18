"""Add answer hooks to online responses only; downloadable originals stay intact."""
import re
from html import escape


def report(ok, prompt="''", given="''", correct="''"):
    return f"window.recordLearningGameAnswer?.({ok},{prompt},{given},{correct});"


# Exact source anchors keep each hook next to the game's own correctness check.
# No DOM guessing: only actual checked answers count as solutions.
HOOKS = {
    'oh-yo': [
        ("s.answered=true;s.lastCorrect=ok;", report('ok', "typeof d!=='undefined'?d.variant:q.q", 'a', "typeof d!=='undefined'?d.answer:q.a")),
    ],
    'autumn-leaves': [("const correct=letter===q.answer;", report('correct','q.variant','letter','q.answer'))],
    'autumn-herbarium': [("const epoch=state.epoch;if(letter===item.answer)", None)],
    'suffixes-nouns': [("if (selectedIndex === question.correct) {", None)],
    'fluffs': [("if (selectedIndex === question.correct) {", None)],
    'homogeneous-members-magic': [("const isCorrect = normalize(selected) === normalize(task.correct);", report('isCorrect','task.prompt || task.sentence','selected','task.correct'))],
    'berry-season-ik-ek': [("if(chosenLetter === item.answer){", None)],
    'paronyms': [("const isCorrect = words.every((word) => normalize(state.assignments[word]) === normalize(word));", report('isCorrect','words','state.assignments','words'))],
    'numerals-hit-parade': [("function recordAttempt(ok,given,correct){", report('ok','STAGES[state.stage].tasks[state.index].question','given','correct'))],
    'karaoke-numerals': [
        ('const correct = variants.includes(normalize(event.target.value));',report('correct','item.question || item.prompt || item.text','event.target.value','item.answer')),
        ('const reference = (expected[index] || "—").split("|")[0];',report('ok',"'Караоке: пропуск '+(index+1)",'input.value','reference')),
    ],
    'summer-gerund-bar': [
        ('const ok=accepted.some(answer=>sameIndices(got,answer));',report('ok','t.text || t.sentence','got','accepted')),
        ("if(ok)state.lessonScores[i]=",None),
    ],
    'mouse-space': [('const pick = state.currentOptions[side];',report('pick.correct','state.currentQ.word','pick.text || side','state.currentQ.full'))],
    'verb-conjugation-quest': [
        ('if (answer === question.correct) {',None),
        ('if (answer === task.answer) {',None),
        ('const correct = normalizeLetter(letter) === normalizeLetter(task.correct_letter);',report('correct','task.variant','letter','task.correct_letter')),
    ],
    'grammar-zoo': [("function finish(ok,message,rightText=''){",report('ok',"document.querySelector('#taskCard')?.innerText || ''",'message',"rightText || answerText()"))],
    'parts-of-speech-kingdom': [('const real = card.cat;',report('real === targetCat','card.raw','CAT[targetCat].name','CAT[real].name'))],
    'butterflies-participle-suffixes': [("if(value===String(items[current].answer).trim().toLowerCase()){",None)],
    'orthoshooting': [('function answer(v){let ok=v===q.correct,',None)],
    'expedition-memory-isolated-members': [('const ok=isCorrect();',report('ok','currentTask.prompt','state.answer || state.matches','currentTask.answer || currentTask.correct || currentTask.pairs'))],
    'syntactic-soup': [
        ('const isCorrect = selectedRelation === task.relation;',report('isCorrect','task.phrase || task.sentence','selectedRelation','task.relation')),
        ('state.transformAttempts += 1;',report('accepted.includes(normalized)','task.phrase || task.sentence','input.value','task.answers')),
    ],
    'foxwarts-syntax': [
        ('state.quizAttempts += 1;',report('sameSet(state.quizSelected, q.answer)','q.question','[...state.quizSelected]','q.answer')),
        ('state.roleAttempts += 1;',report('state.roleSelected === task.answer','task.sentence || task.text','state.roleSelected','task.answer')),
        ('state.parsePOSComplete = wrong.length === 0;',report('state.parsePOSComplete','task.sentence','state.parsePOSAssignments','task.pos')),
        ('const wrong = task.units.reduce((list, unit, index) => state.parseAssignments[index] === unit[1] ? list : list.concat(index), []);',report('wrong.length===0','task.sentence','state.parseAssignments','task.units')),
        ('state.parseCharacteristicComplete = CHARACTERISTIC_FIELDS.every(field => state.parseCharacteristics[field.key] === task.features[field.key]);',report('state.parseCharacteristicComplete','task.sentence','state.parseCharacteristics','task.features')),
    ],
    'participle-map': [
        ('function recordTaskResult(locationId,taskId,ok){',report('ok','locationId+": "+taskId')),
        ("run.answered=true;$('#feedback').textContent=detail+",None),
        ('function completeMemo(t){',report('true','t.title || t.id')),
    ],
    'word-architecture': [
        ('let t=statsFor(q.skill);t.total++;',report('ok','q.word || q.prompt || q.id','state.mark','q.answer')),
        ("if(correct){x.solved=true;",None),
    ],
    'palace-restoration': [("let ids=d.assembly.map(t=>t.id),candidate=duelCandidate(ids);",report("!!candidate&&!d.built.has(candidate.lemma)","'Сборка слова из морфем'",'duelWritten(ids)',"candidate?.word || ''"))],
    'truth-action-oge': [("function completeCard(outcome) {",report("outcome==='done'","'Оценка участника: '+getActiveTaskLabel()",'outcome',"'Выполнено'"))],
    'butterflies-participial-phrase': [
        ('x("good",n),h("good"),f(e=>[...e,u.id])',None),
        ('x("bad",n),h("bad")',None),
    ],
}
ALIASES = {'berry-season':'berry-season-ik-ek','butterflies':'butterflies-participle-suffixes'}


def transform(slug, body, html=False):
    slug = ALIASES.get(slug, slug)
    text = body.decode('utf-8-sig')
    for anchor, code in HOOKS.get(slug, []):
        if anchor not in text:
            continue
        if code is not None:
            text = text.replace(anchor, anchor + code)
        elif slug == 'autumn-herbarium':
            text = text.replace(anchor, 'const epoch=state.epoch;' + report('letter===item.answer','item.variant','letter','item.answer') + 'if(letter===item.answer)')
        elif slug in {'suffixes-nouns','fluffs'}:
            text = text.replace(anchor, report('selectedIndex===question.correct','question.text || question.word || question.question','question.options[selectedIndex]','question.options[question.correct]') + anchor)
        elif slug == 'berry-season-ik-ek':
            text = text.replace(anchor, report('chosenLetter===item.answer','item.variant','chosenLetter','item.answer') + anchor)
        elif slug == 'verb-conjugation-quest':
            q = 'question' if 'question.correct' in anchor else 'task'
            answer = q + ('.correct' if q == 'question' else '.answer')
            text = text.replace(anchor, report('answer==='+answer,q+'.prompt || '+q+'.word','answer',answer) + anchor)
        elif slug == 'butterflies-participle-suffixes':
            text = text.replace(anchor, report('value===String(items[current].answer).trim().toLowerCase()','items[current].variant','value','items[current].answer') + anchor)
        elif slug == 'orthoshooting':
            text = text.replace(anchor, 'function answer(v){' + report('v===q.correct','q.word || q.question','v','q.correct') + 'let ok=v===q.correct,')
        elif slug == 'participle-map':
            text = text.replace(anchor, report('ok','t.text || t.title || t.id','Array.from(selected || [])','t.correct') + anchor)
        elif slug == 'summer-gerund-bar':
            text = text.replace(anchor, report('ok','t.text || t.question','got','expected || t.answers') + anchor)
        elif slug == 'word-architecture':
            text = text.replace(anchor, report('correct',"'Мини-игра: '+id",'value','q') + anchor)
        elif slug == 'butterflies-participial-phrase':
            code = report('true' if 'good' in anchor else 'false','u.text || u.sentence || u.id','d','C.commas').rstrip(';')
            text = text.replace(anchor, code + ',' + anchor)
    if slug == 'butterflies-participle-suffixes':
        anchor = 'if (value === answer) {'
        text = text.replace(anchor, report('value===answer','items[current].variant','value','answer') + anchor)
    if html:
        tag = f'<script src="/game-tracker.js?v=20261018" data-game="{escape(slug, quote=True)}"></script>'
        text = re.sub(r'(<head[^>]*>)', lambda m: m[0] + tag, text, count=1, flags=re.I)
    return text.encode('utf-8')
