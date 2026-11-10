/* Speech trainers use the application's shared navigation, checks and statistics. */
const speechMode=(title,hint)=>({title,hint,eyebrow:'культура речи'});
const speechErrors=speechMode('Копилка ошибок','Повторение до трёх правильных ответов');
const speechModes={
 ege4:{stress:speechMode('Поставить ударение','Выделите ударную гласную'),truth:speechMode('Верно / неверно','Проверьте ударение в слове'),exam:speechMode('Формат ЕГЭ','Выберите слова с верным ударением'),errors:speechErrors},
 ege6:{rule:speechMode('По правилу','Редактирование предложений'),exam:speechMode('Формат ЕГЭ','Исправьте лексическую ошибку'),errors:speechErrors},
 ege7:{fix:speechMode('Исправь ошибку','Впишите правильную форму'),truth:speechMode('Правильно / неправильно','Если неправильно — исправьте'),choice:speechMode('Как правильно?','Выбор из вариантов'),exam:speechMode('Режим ЕГЭ','Пять сочетаний, одна ошибка'),errors:speechErrors},
 ege8:{rule:speechMode('По правилу','Выберите вид грамматической ошибки'),truth:speechMode('Верно / неверно','Оцените предложение'),classify:speechMode('Определи тип ошибки','Одно предложение — один ответ'),exam:speechMode('Формат ЕГЭ','Соедините предложение с типом ошибки линией'),errors:speechErrors},
 'speech-ege':{ege_exam_mix:speechMode('Сборная тренировка','Выберите количество каждого задания 1–8')}
};
const speechTasks=Array.from({length:8},(_,i)=>({id:'ege'+(i+1),title:'Задание '+(i+1),hint:['Средства связи','Значение слова','Характеристики текста','Ударение','Паронимы','Лексические нормы','Морфологические нормы','Грамматические нормы'][i],disabled:false}));
function currentMixTasks(){return state.currentActivity==='speech-ege'?speechTasks:orthographyEgeTasks;}
// One topic picker for speech, grammar and text trainers. Empty saved selection means all topics.
function renderTopicPicker(rules, selected, title='Темы') {
 const ids=Array.isArray(selected)?selected:selected?[selected]:rules.map(r=>r.rule_id);
 return `<section class="rule-picker"><h3>${escapeHtml(title)}</h3><div class="rule-check-list"><label class="rule-check"><input type="checkbox" data-topic-all ${rules.every(r=>ids.includes(r.rule_id))?'checked':''}><span>Все темы</span></label>${rules.map(r=>{const p=state.bootstrap.rule_progress?.[r.rule_id];return `<label class="rule-check"><input type="checkbox" data-topic-id="${escapeHtml(r.rule_id)}" ${ids.includes(r.rule_id)?'checked':''}><span>${escapeHtml(r.rule_name)}</span><small>${p?`${p.solved}/${p.total} · ${pct(p.solved,p.total)}`:r.count}</small></label>`;}).join('')}</div></section>`;
}
function bindTopicPicker(root,rules,onChange) {
 root.querySelector('[data-topic-all]')?.addEventListener('change',e=>onChange(e.target.checked?rules.map(r=>r.rule_id):[]));
 root.querySelectorAll('[data-topic-id]').forEach(input=>input.addEventListener('change',()=>onChange([...root.querySelectorAll('[data-topic-id]')].filter(i=>i.checked).map(i=>i.dataset.topicId))));
}
function renderSpeechSetup(){
 const root=document.querySelector('#setupView');
 root.innerHTML=`${state.currentActivity==='ege7'?'<p class="muted">В базе 420 сочетаний: 371 пара с ошибкой и 49 нормативных форм. В режимах «Исправь ошибку» и «Как правильно?» используются только 371 полная пара. Остальные 49 форм доступны в проверке нормы и как правильные сочетания ЕГЭ.</p>':''}<div class="setup-grid"><label>Количество вопросов<input id="speechCount" type="number" min="1" max="30" value="${state.questionCount}"></label><button class="primary-button" id="startPractice">Начать</button></div>${(['ege7','ege8'].includes(state.currentActivity)||state.mode==='rule')?renderTopicPicker(Object.values(state.bootstrap.rules).flat(),state.speechTopics?.[state.currentActivity],state.currentActivity==='ege7'?'Части речи':'Виды ошибок'):''}${state.mode==='errors'?'<p class="muted">Ошибки из тренировок и тестов. Три правильных повторения убирают ошибку из копилки.</p>':''}`;
 root.querySelector('#speechCount').onchange=e=>{state.questionCount=Math.max(1,Math.min(30,Math.trunc(Number(e.target.value)||1)));e.target.value=state.questionCount;};
 root.querySelector('#startPractice').onclick=startPractice;
 if((['ege7','ege8'].includes(state.currentActivity)||state.mode==='rule')){const rules=Object.values(state.bootstrap.rules).flat();bindTopicPicker(root,rules,ids=>{state.speechTopics||={};state.speechTopics[state.currentActivity]=ids;state.selectedRuleIds=ids;renderSpeechSetup();});if(state.speechTopics?.[state.currentActivity]?.length===0)root.querySelector('#startPractice').disabled=true;}
}
function renderSpeechQuestion(q,index){
 const id=escapeHtml(q.question_id),a=state.answers[q.question_id];
 let body='';
 if(q.kind==='speech_truth')body=`<p class="word-prompt">${escapeHtml(q.prompt)}</p><div class="choice-row">${[['true','Правильно'],['false','Неправильно']].map(([v,label])=>`<button class="choice ${a?.verdict===v?'selected':''}" data-speech-verdict="${v}" data-question-id="${id}">${label}</button>`).join('')}</div>${a?.verdict==='false'?`<label>Исправленное слово<input data-speech-correction data-question-id="${id}" value="${escapeHtml(a?.word||'')}" autocomplete="off"></label>`:''}`;
 else if(q.kind==='speech_stress')body=`<div class="speech-word">${[...q.prompt].map((c,i)=>/[аеёиоуыэюя]/i.test(c)?`<button class="speech-vowel ${a===String(i)?'selected':''}" type="button" data-question-id="${id}" data-answer="${i}" aria-label="Ударение на ${i+1}-ю букву">${escapeHtml(a===String(i)?c.toUpperCase():c)}</button>`:escapeHtml(c)).join('')}</div><p>${escapeHtml(q.context||'')}</p>`;
 else if(q.kind==='speech_multi')body=q.rows.map((r,i)=>`<button class="line-row ${(a||'').includes(String(i+1))?'selected':''}" data-question-id="${id}" data-answer="${i+1}" data-multi="true"><b>${i+1}</b><span>${escapeHtml(r)}</span></button>`).join('');
 else if(q.kind==='speech_match')body=`<p class="muted">Выберите тип ошибки слева, затем предложение справа. Повторный выбор меняет соединение.</p><p class="speech-mobile-note muted">Прокручивайте карточки по горизонтали, чтобы видеть обе колонки.</p><div class="speech-match-scroll" tabindex="0" role="region" aria-label="Соединение типов ошибок и предложений"><div class="speech-match" data-match="${id}"><svg aria-hidden="true"></svg><div>${q.types.map(t=>`<button class="line-row ${state.speechLink===id+':'+t.id?'selected':''}" data-link-type="${t.id}" data-question-id="${id}" aria-pressed="${state.speechLink===id+':'+t.id}"><b>${t.id}</b><span>${escapeHtml(t.label)}${a?.[t.id]?' → '+a[t.id]:''}</span></button>`).join('')}</div><div>${q.sentences.map((t,i)=>`<button class="line-row ${Object.values(a||{}).includes(String(i+1))?'selected':''}" data-link-sentence="${i+1}" data-question-id="${id}"><b>${i+1}</b><span>${escapeHtml(t)}</span></button>`).join('')}</div></div></div>`;
 else body=`<p class="word-prompt">${escapeHtml(q.prompt)}</p>${q.kind==='speech_input'?`<label class="answer-input-label">Ваш ответ<input data-review-answer data-question-id="${id}" value="${escapeHtml(a||'')}" aria-label="Ваш ответ" autocomplete="off" spellcheck="false" placeholder="Введите слово"></label>`:`<div class="choice-row">${q.choices.map(c=>`<button class="choice ${a===c.value?'selected':''}" data-question-id="${id}" data-answer="${escapeHtml(c.value)}">${escapeHtml(c.label)}</button>`).join('')}</div>`}`;
 return `<article class="question speech-question"><div class="question-head"><span>Задание ${index+1}</span><span>${escapeHtml(q.kind==='speech_match'?'Формат ЕГЭ':q.kind==='speech_choice' && q.choices?.length>2?'Определите ответ':q.rule_name)}</span></div><p>${escapeHtml(q.instruction|| (['speech_multi','speech_match'].includes(q.kind)?q.prompt:''))}</p>${body}</article>`;
}
function bindSpeechAnswers(root){
 root.querySelectorAll('[data-speech-verdict]').forEach(b=>b.onclick=()=>{state.answers[b.dataset.questionId]={verdict:b.dataset.speechVerdict,word:state.answers[b.dataset.questionId]?.word||''};renderQuestions();});
 root.querySelectorAll('[data-speech-correction]').forEach(e=>e.oninput=()=>{state.answers[e.dataset.questionId]={...state.answers[e.dataset.questionId],word:e.value};});
 root.querySelectorAll('[data-link-type]').forEach(b=>b.onclick=()=>{state.speechLink=b.dataset.questionId+':'+b.dataset.linkType;renderQuestions();});
 root.querySelectorAll('[data-link-sentence]').forEach(b=>b.onclick=()=>{
   const id=b.dataset.questionId,prefix=id+':';if(!state.speechLink?.startsWith(prefix))return;
   const type=state.speechLink.slice(prefix.length),answers={...(state.answers[id]||{})};
   for(const k of Object.keys(answers))if(answers[k]===b.dataset.linkSentence)delete answers[k];
   answers[type]=b.dataset.linkSentence;state.answers[id]=answers;state.speechLink=null;renderQuestions();
 });
 if(typeof requestAnimationFrame==='function')requestAnimationFrame(drawSpeechLines);
}
function drawSpeechLines(){document.querySelectorAll('[data-match]').forEach(box=>{
 const svg=box.querySelector('svg'),r=box.getBoundingClientRect(),a=state.answers[box.dataset.match]||{};
 svg.setAttribute('viewBox',`0 0 ${r.width} ${r.height}`);
 svg.innerHTML=Object.entries(a).map(([k,v])=>{
 const left=box.querySelector(`[data-link-type="${k}"]`)?.getBoundingClientRect(),right=box.querySelector(`[data-link-sentence="${v}"]`)?.getBoundingClientRect();
 return left&&right?`<line x1="${left.right-r.left}" y1="${left.top+left.height/2-r.top}" x2="${right.left-r.left}" y2="${right.top+right.height/2-r.top}" stroke="var(--accent,#678c65)" stroke-width="3"/>`:'';
 }).join('');
});}
window.addEventListener('resize',drawSpeechLines);

function isSpeechPractice(){return ['ege4','ege6','ege7','ege8','speech-ege'].includes(state.currentActivity);}
function renderSpeechPractice(){
 const session=state.currentSession,index=state.currentQuestionIndex||0,q=session.questions[index];
 if(!q)return;
 const root=document.querySelector('#practiceView'),results=session.checked_results||{},result=results[q.question_id],busy=Boolean(session.checking);
 document.querySelector('#resultView').classList.add('hidden');root.classList.remove('hidden');
 const automatic=['speech_choice','speech_stress','text_lab_bool','paronym_choice'].includes(q.kind);
 root.innerHTML=`<div class="assignment-progress"><label>Вопрос ${index+1} из ${session.questions.length}</label><progress max="${session.questions.length}" value="${Object.keys(results).length}"></progress></div>
 ${renderQuestion(q,index)}
 ${result?`<div class="result-item ${result.is_correct?'ok':'bad'}" data-speech-feedback role="status"><b>${result.is_correct?'Верно':'Неверно'}</b><p>Правильный ответ: ${escapeHtml(formatAssignedAnswer(result.correct_answer))}</p><p>${escapeHtml(result.explanation||'')}</p></div>`:''}
 <p class="error" data-speech-error role="alert"></p>
 <div class="practice-actions"><button class="ghost-button" data-speech-menu ${busy?'disabled':''}>К меню</button>${result?`<button class="primary-button" data-speech-next>${index+1<session.questions.length?'Следующий вопрос':'Завершить тренировку'}</button>`:!automatic?`<button class="primary-button" data-speech-check ${busy?'disabled':''}>${busy?'Проверяем…':'Проверить ответ'}</button>`:`<span class="muted" aria-live="polite">${busy?'Проверяем…':'Нажмите на '+(q.kind==='speech_stress'?'ударную гласную':'ответ')+' — проверка сразу.'}</span>`}</div>`;
 bindQuestionAnswers(root);
 if(result||busy)root.querySelectorAll('.question button,.question input,.question select').forEach(e=>e.disabled=true);
 root.querySelector('[data-speech-menu]').onclick=backToMenu;
 root.querySelector('[data-speech-check]')?.addEventListener('click',checkSpeechAnswer);
 root.querySelector('[data-review-answer]')?.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();checkSpeechAnswer();}});
 root.querySelector('[data-speech-next]')?.addEventListener('click',()=>{
   if(index+1<session.questions.length){state.currentQuestionIndex++;state.startedAt=Date.now();renderSpeechPractice();}
   else renderResults({results:session.questions.map(q=>results[q.question_id]),correct:Object.values(results).filter(r=>r.is_correct).length,total:session.questions.length});
 });
}
async function checkSpeechAnswer(){
 const session=state.currentSession,q=session?.questions[state.currentQuestionIndex||0];
 if(!q||session.checking||session.checked_results?.[q.question_id])return;
 if(!answerIsComplete(q)){document.querySelector('[data-speech-error]').textContent='Сначала ответьте на задание.';return;}
 session.checking=true;renderSpeechPractice();
 try{
  const result=await api(activityApi('/practice/check'),{method:'POST',body:JSON.stringify({session_id:session.session_id,question_id:q.question_id,answer:state.answers[q.question_id],time_spent_sec:Math.round((Date.now()-state.startedAt)/1000)})});
  session.checked_results||={};session.checked_results[q.question_id]=result;session.checking=false;
  if(state.currentSession===session)renderSpeechPractice();
 }catch(err){session.checking=false;if(state.currentSession===session){renderSpeechPractice();document.querySelector('[data-speech-error]').textContent=err.message;}}
}
function autoCheckSpeechChoice(questionId){
 if(!isSpeechPractice()||state.currentSession?.assignment_id)return;
 const q=state.currentSession?.questions[state.currentQuestionIndex||0];
 if(q?.question_id===questionId&&['speech_stress','speech_choice','text_lab_bool','paronym_choice'].includes(q.kind))checkSpeechAnswer();
}
