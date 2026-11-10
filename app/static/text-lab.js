/* The text lab uses the same state, assignments, server checks and progress as every trainer. */
const textLabModes = {
  gap: {title:'Задание 1 · Пропуск',hint:'Части речи и средства связи',eyebrow:'точечная отработка'},
  lex: {title:'Задание 2 · Значение слова',hint:'Одна словарная статья',eyebrow:'лексика'},
  truth: {title:'Задание 3 · Верно / неверно',hint:'Одно утверждение о тексте',eyebrow:'особенности текста'},
  characteristics: {title:'Задание 3 · Все верные',hint:'Пять характеристик: выберите все верные',eyebrow:'формат задания 3'},
  exam: {title:'Формат ЕГЭ · Задания 1–3',hint:'Три полных задания к случайному тексту',eyebrow:'работа с текстом'},
  errors: {title:'Копилка ошибок',hint:'Повторение до 3 правильных ответов',eyebrow:'личное повторение'},
};

function textLabRules(mode) {
  const category=mode==='gap'?'Задание 1':['truth','characteristics'].includes(mode)?'Задание 3':null;
  return category ? state.bootstrap.rules[category] || [] : [];
}

function textLabTopicControl(mode, selected) {
 const rules=textLabRules(mode);
 return rules.length?renderTopicPicker(rules,selected,mode==='gap'?'Часть речи':'Стиль речи'):'';
}

function textLabSourceCredit(){return '<p class="text-lab-credit"><a href="#text-lab-source" data-text-lab-source>Тексты из сборников Р.А. Дощинского 2025, 2026 года</a></p>';}

function bindTextLabSource(root){root.querySelectorAll('[data-text-lab-source]').forEach(a=>a.onclick=e=>{e.preventDefault();const modal=learningModal('Источники текстов');modal.querySelector('[data-content]').innerHTML='<p>Тексты из сборников Р.А. Дощинского 2025, 2026 года.</p>';});}

function renderTextLabSetup() {
  const root=document.querySelector('#setupView'),mode=state.mode;
  const selected=state.textLabTopics?.[mode];
  const rules=textLabRules(mode);
  root.innerHTML=`<p class="muted">${escapeHtml(textLabModes[mode].hint)}.${mode==='exam'?' Один текст — три задания; проверка после завершения всей тренировки.':''}</p>
    <div class="setup-grid"><label>Количество ${mode==='exam'?'текстов (по 3 задания)':'вопросов'}<input id="questionCount" type="number" min="1" max="30" value="${state.questionCount}"></label><button class="primary-button" id="startPractice">Начать</button></div>
    ${textLabTopicControl(mode,selected)}
    ${mode==='errors'?'<p class="muted">Здесь собраны ошибки из тренировок и назначенных тестов. Ошибка возвращается на три правильных повторения.</p>':''}${textLabSourceCredit()}`;
  root.querySelector('#questionCount').onchange=e=>{state.questionCount=Math.max(1,Math.min(30,Number(e.target.value)||10));e.target.value=state.questionCount;};
  root.querySelector('#startPractice').onclick=startPractice;
  bindTopicPicker(root,rules,ids=>{state.textLabTopics||={};state.textLabTopics[mode]=ids;renderTextLabSetup();});
  if(rules.length&&Array.isArray(selected)&&!selected.length)root.querySelector('#startPractice').disabled=true;
  bindTextLabSource(root);
}

function textLabContext(question) {
  const text=question.text||'',ranges=[...(question.highlight_ranges||[])].sort((a,b)=>a[0]-b[0]);let html='',end=0;
  for(const [a,b] of ranges){if(a<end)continue;html+=escapeHtml(text.slice(end,a))+'<mark>'+escapeHtml(text.slice(a,b))+'</mark>';end=b;}
  html+=escapeHtml(text.slice(end));
  return html.replace(/&lt;\.{3}&gt;/g,'<span class="text-lab-gap">‹ пропуск ›</span>').replace(/\r\n?/g,'\n').trim().split(/\n[ \t]*\n+/).map(p=>'<p>'+p.replace(/[ \t]*\n[ \t]*/g,' ')+'</p>').join('');
}

function renderTextLabQuestion(question,index) {
  const id=escapeHtml(question.question_id),answer=state.answers[question.question_id]||'';
  let controls='';
  if(question.kind==='text_lab_gap')controls=`<label>Ваш ответ<input data-text-lab-free="${id}" value="${escapeHtml(answer)}" autocomplete="off" spellcheck="false" placeholder="Введите слово или сочетание"></label>`;
  else if(question.kind==='text_lab_bool')controls=`<p class="text-lab-statement">${escapeHtml(question.statement)}</p><div class="choice-row">${[['true','Верно'],['false','Неверно']].map(([value,label])=>`<button class="choice ${answer===value?'selected':''}" data-question-id="${id}" data-answer="${value}">${label}</button>`).join('')}</div>`;
  else controls=`<p class="muted">Выберите все верные варианты ответов.</p><div class="text-lab-options">${question.options.map(o=>`<label class="text-lab-option"><input type="checkbox" data-text-lab-choice="${o.n}" data-question-id="${id}" ${String(answer).includes(String(o.n))?'checked':''}><span><b>${o.n}.</b> ${escapeHtml(o.text)}</span></label>`).join('')}</div>`;
  return `<article class="question text-lab-question"><div class="question-head"><span>Вопрос ${index+1} · Задание ${question.task_number}</span></div><div class="text-lab-layout"><section class="text-lab-context"><h3>Исходный текст</h3>${question.task_number===2?'<p class="muted">Сопоставьте выделенные слова со словарным толкованием.</p>':''}${textLabContext(question)}</section><section class="text-lab-exercise"><p>${escapeHtml(question.prompt)}</p>${controls}</section></div>${textLabSourceCredit()}</article>`;
}

function bindTextLabAnswers(root) {
  bindTextLabSource(root);
  root.querySelectorAll('[data-text-lab-free]').forEach(input=>input.addEventListener('input',()=>{state.answers[input.dataset.textLabFree]=input.value;queueAssignedSave();}));
  root.querySelectorAll('[data-text-lab-choice]').forEach(input=>input.addEventListener('change',()=>{const id=input.dataset.questionId,values=new Set(String(state.answers[id]||'').split('').filter(Boolean));input.checked?values.add(input.dataset.textLabChoice):values.delete(input.dataset.textLabChoice);state.answers[id]=[...values].sort().join('');queueAssignedSave();}));
}

function renderTextLabPractice() {
  const session=state.currentSession,root=document.querySelector('#practiceView'),index=state.currentQuestionIndex||0,q=session.questions[index];
  const results=session.checked_results||{},result=results[q.question_id],exam=session.mode==='exam';
  root.classList.remove('hidden');
  root.innerHTML=`<div class="assignment-progress"><label>Вопрос ${index+1} из ${session.questions.length}</label><progress max="${session.questions.length}" value="${Object.keys(results).length||index}"></progress></div>
    ${renderQuestion(q,index)}
    ${result?`<div class="result-item ${result.is_correct?'ok':'bad'}" role="status"><b>${result.is_correct?'Верно':'Есть ошибка'}</b><p>Ваш ответ: ${escapeHtml(result.given_answer)} · правильно: ${escapeHtml(result.correct_answer)}</p><p class="text-lab-explanation">${escapeHtml(result.explanation||'')}</p></div>`:''}
    <p class="error" data-text-lab-error role="alert"></p><div class="practice-actions"><button class="ghost-button" data-text-lab-menu>К меню</button><button class="secondary-button" data-text-lab-prev ${index?'':'disabled'}>Предыдущее</button>${!exam&&!result?'<button class="primary-button" data-text-lab-check>Проверить ответ</button>':''}${index+1<session.questions.length?'<button class="secondary-button" data-text-lab-next>Следующий вопрос</button>':'<button class="primary-button" id="submitPractice">Завершить и проверить</button>'}</div>`;
  bindQuestionAnswers(root);
  if(result)root.querySelectorAll('.question button,.question input').forEach(el=>el.disabled=true);
  root.querySelector('[data-text-lab-menu]').onclick=backToMenu;
  root.querySelector('[data-text-lab-prev]').onclick=()=>{state.currentQuestionIndex--;renderTextLabPractice();};
  root.querySelector('[data-text-lab-next]')?.addEventListener('click',()=>{state.currentQuestionIndex++;renderTextLabPractice();});
  root.querySelector('#submitPractice')?.addEventListener('click',submitPractice);
  root.querySelector('[data-text-lab-check]')?.addEventListener('click',async e=>{
    if(!answerIsComplete(q)){root.querySelector('[data-text-lab-error]').textContent='Введите ответ или выберите варианты.';return;}
    e.target.disabled=true;
    try{const checked=await api(activityApi('/practice/check'),{method:'POST',body:JSON.stringify({session_id:session.session_id,question_id:q.question_id,answer:state.answers[q.question_id],time_spent_sec:Math.round((Date.now()-state.startedAt)/1000)})});session.checked_results||={};session.checked_results[q.question_id]=checked;if(state.currentSession===session)renderTextLabPractice();}
    catch(err){if(state.currentSession===session){root.querySelector('[data-text-lab-error]').textContent=err.message;e.target.disabled=false;}}
  });
}

function collectTextLabTestConfig(root) {
  const topics=[...root.querySelectorAll('[data-topic-id]')].filter(i=>i.checked).map(i=>i.dataset.topicId);
  return {activity:'ege1-3',mode:root.querySelector('#testMode').value,count:Number(root.querySelector('#testCount').value),rule_ids:topics,include_errors:Boolean(root.querySelector('#testIncludeErrors')?.checked)};
}

function showTextLabTestComposer() {
  const backdrop=document.createElement('div');backdrop.className='modal-backdrop';
  backdrop.innerHTML=`<section class="progress-modal"><div class="panel-head"><h2>Составить тест · Задания 1–3</h2><button class="secondary-button" data-close>Закрыть</button></div><div class="setup-grid"><label>Режим<select id="testMode">${Object.entries(textLabModes).map(([mode,meta])=>`<option value="${mode}">${escapeHtml(meta.title)}</option>`).join('')}</select></label><label><span data-count-label>Количество вопросов</span><input id="testCount" type="number" min="1" max="60" value="${Math.min(60,state.questionCount)}"></label></div><div data-topic-control></div><label class="manual-toggle" data-include-errors><input id="testIncludeErrors" type="checkbox">Добавить вопросы из копилок ошибок моих учеников</label><p class="muted" data-composer-hint></p><p class="error" id="testComposerError"></p><div class="practice-actions"><button class="primary-button" id="downloadTest">Скачать .txt</button></div></section>`;
  document.body.append(backdrop);attachAssignmentComposer(backdrop);
  backdrop.querySelector('[data-close]').onclick=()=>backdrop.remove();
  function mountTopics(mode,selected){
    backdrop.querySelector('[data-topic-control]').innerHTML=textLabTopicControl(mode,selected);
    const rules=textLabRules(mode),empty=rules.length&&Array.isArray(selected)&&!selected.length;
    backdrop.querySelector('#downloadTest').disabled=Boolean(empty);
    bindTopicPicker(backdrop,rules,ids=>mountTopics(mode,ids));
  }
  function refresh(){
    const mode=backdrop.querySelector('#testMode').value;
    mountTopics(mode);
    const include=backdrop.querySelector('#testIncludeErrors');include.checked=false;
    backdrop.querySelector('[data-include-errors]').classList.toggle('hidden',['exam','errors'].includes(mode));
    backdrop.querySelector('[data-count-label]').textContent=mode==='exam'?'Количество текстов (по 3 задания)':'Количество вопросов';
    backdrop.querySelector('[data-composer-hint]').textContent=mode==='errors'?'Тест составляется из ошибок ваших учеников.':mode==='exam'?'Каждый текст добавляет три отдельных задания. Тест и ключи фиксируются при назначении.':'Можно выбрать несколько тем одновременно.';
  }
  backdrop.querySelector('#testMode').value=state.mode;backdrop.querySelector('#testMode').onchange=refresh;refresh();
  backdrop.querySelector('#downloadTest').onclick=async e=>{e.target.disabled=true;try{await downloadRequest('/api/teacher/test','ege1-3-test.txt',{method:'POST',body:JSON.stringify(collectTextLabTestConfig(backdrop))});}catch(err){backdrop.querySelector('#testComposerError').textContent=err.message;}finally{e.target.disabled=false;}};
}
