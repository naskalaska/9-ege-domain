const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {spawn}=require('node:child_process');
const root=path.resolve(__dirname,'..'),qa=path.join(root,'maintenance/offline-qa');
const fixture=JSON.parse(fs.readFileSync(path.join(qa,'statistics-fixtures.json'),'utf8'));
const delay=ms=>new Promise(r=>setTimeout(r,ms));
const chrome=spawn('C:/Program Files/Google/Chrome/Application/chrome.exe',[
 '--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check',
 '--remote-debugging-port=9238','--remote-allow-origins=*','--user-data-dir='+path.join(qa,'statistics-browser'),'about:blank'
],{windowsHide:true,stdio:'ignore'});
(async()=>{
 let ws;
 try{
  let tabs;
  for(let n=0;n<60;n++){try{tabs=await(await fetch('http://127.0.0.1:9238/json')).json();break}catch{await delay(200)}}
  assert(tabs,'Chrome did not start');
  ws=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl);await new Promise(r=>ws.onopen=r);
  let seq=0;const pending=new Map(),errors=[];
  ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(Error(JSON.stringify(m.error))):p.resolve(m.result)}else if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails)};
  const send=(method,params={})=>new Promise((resolve,reject)=>{const id=++seq;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}))});
  const evaluate=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||JSON.stringify(r.exceptionDetails));return r.result.value;};
  const until=async expression=>{for(let n=0;n<100;n++){if(await evaluate(expression))return;await delay(100)}throw Error('Timeout: '+expression)};
  const screenshot=async name=>{const shot=await send('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(qa,name+'.png'),Buffer.from(shot.data,'base64'))};
  await send('Runtime.enable');await send('Page.enable');await send('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
  await send('Page.navigate',{url:'http://127.0.0.1:8098/login'});await until(`typeof state!=='undefined' && typeof api==='function'`);
  await evaluate(`(async()=>{const d=await api('/api/login',{method:'POST',body:JSON.stringify({email:'teacher',password:'teacher123'})});state.user=d.user;state.token=d.token;localStorage.setItem('ege_token',d.token);await loadActivity('ege9')})()`);
  for(const activity of ['ege10','ege11','ege12','ege13','ege14','ege15','ege5','orthography-ege','html-games','ege9']){
    await evaluate(`document.querySelector('[data-platform-activity="${activity}"]').click()`);
    await until(`state.currentActivity===${JSON.stringify(activity)} && Boolean(document.querySelector('[data-platform-activity="${activity}"][aria-current="page"]'))`);
  }
  await evaluate(`showProgress()`);await until(`document.querySelectorAll('.statistics-student').length===2`);
  assert.equal(await evaluate(`document.querySelectorAll('.statistics-student[open]').length`),0);
  assert.equal(await evaluate(`document.querySelector('.statistics-metrics b').textContent`),String(fixture.summary.total));
  await screenshot('statistics-teacher-collapsed');
  await evaluate(`document.querySelector('[data-student-id="${fixture.student_id}"]').open=true`);
  await until(`Boolean(document.querySelector('[data-student-body] .statistics-answer'))`);
  assert.equal(await evaluate(`document.querySelectorAll('[data-student-body] tbody tr').length>=10`),true);
  const total=await evaluate(`Number(document.querySelector('[data-history-results] b').textContent)`);assert(total>80);
  await evaluate(`(()=>{const f=document.querySelector('.statistics-history-filters');f.elements.activity.value='ege11';f.elements.kind.value='details';f.requestSubmit()})()`);
  await until(`Boolean(document.querySelector('[data-history-results]')?.textContent.includes('Правильный ответ (номера строк)'))`);
  const diagnostic=await evaluate(`(()=>{const a=document.querySelector('.statistics-answer');return {labels:[...a.querySelectorAll('dt')].map(e=>e.textContent),values:[...a.querySelectorAll('dd')].map(e=>e.textContent),prompt:a.querySelector('.statistics-prompt').textContent}})()`);
  assert.deepEqual(diagnostic.values.slice(0,2),[fixture.row_given || '15',fixture.row_key]);
  assert.equal(diagnostic.labels[2],'Буква в этом слове');
  assert(!diagnostic.prompt.includes('Выберите все строки'));
  await evaluate(`document.querySelector('.statistics-answer').scrollIntoView({block:'center'})`);
  await screenshot('statistics-row-answer');
  await evaluate(`(()=>{const f=document.querySelector('.statistics-history-filters');f.elements.activity.value='';f.elements.kind.value='all';f.requestSubmit()})()`);
  await until(`Number(document.querySelector('[data-history-results] b')?.textContent)>80`);
  await evaluate(`document.querySelector('[data-history-next]').click()`);await until(`document.querySelector('[data-history-page]').textContent.includes('2 из')`);
  await evaluate(`(()=>{const f=document.querySelector('.statistics-history-filters');f.elements.search.value='Самая старая';f.requestSubmit()})()`);
  await until(`Boolean(document.querySelector('[data-history-results]')?.textContent.includes('л..сной'))`);
  await evaluate(`(()=>{const f=document.querySelector('.statistics-history-filters');f.elements.search.value='';f.elements.activity.value='games';f.requestSubmit()})()`);
  await until(`Boolean(document.querySelector('[data-history-results]')?.textContent.includes('ц..плёнок'))`);
  assert.match(await evaluate(`document.querySelector('[data-history-results]').textContent`),/Правильный ответ/);
  assert.match(await evaluate(`document.querySelector('[data-history-results]').textContent`),/не сохранены подробности ответа/);
  await evaluate(`document.querySelector('[data-history-results]').scrollIntoView({block:'start'})`);await delay(100);
  await screenshot('statistics-game-errors');
  // Export must contain the old record, even when it is beyond the first pages.
  const exported=await evaluate(`fetch('/api/statistics/export?student_id=${fixture.student_id}&status=incorrect',{headers:{Authorization:'Bearer '+state.token}}).then(r=>r.text())`);
  assert(exported.includes('Самая старая ошибка'));
  await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await delay(150);
  assert(await evaluate(`document.documentElement.scrollWidth<=innerWidth+2`));await screenshot('statistics-mobile');
  await send('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
  await evaluate(`(async()=>{const d=await api('/api/login',{method:'POST',body:JSON.stringify({email:'student',password:'student123'})});state.user=d.user;state.token=d.token;localStorage.setItem('ege_token',d.token);await showOverallStatistics()})()`);
  await until(`Boolean(document.querySelector('[data-own-history] .statistics-answer'))`);
  assert.match(await evaluate(`document.body.innerText`),/Моя общая статистика/);
  assert.match(await evaluate(`document.body.innerText`),/Уверенная тема/);
  assert.equal(await evaluate(`document.querySelectorAll('.statistics-student').length`),0);
  await screenshot('statistics-student');
  // Required letters: cannot bypass, survive resuming, and are checked separately.
  await evaluate(`openAssignedTest(${JSON.stringify(fixture.letter_test_id)})`);
  await evaluate(`document.querySelector('[data-assignment-check]').click()`);
  assert.match(await evaluate(`document.querySelector('[data-assignment-error]').textContent`),/Вставьте буквы/);
  await evaluate(`(()=>{const letters=${JSON.stringify(fixture.letters)};for(const input of document.querySelectorAll('[data-line-letter]')){input.value=letters[input.dataset.lineLetter];input.dispatchEvent(new Event('input',{bubbles:true}))}for(const row of ${JSON.stringify(fixture.letter_key)}) document.querySelector('[data-answer="'+row+'"]').click()})()`);
  await evaluate(`persistAssignedAnswers()`);
  await evaluate(`openAssignedTest(${JSON.stringify(fixture.letter_test_id)})`);
  assert.equal(await evaluate(`document.querySelector('[data-line-letter="0"]').value`),fixture.letters['0']);
  await evaluate(`document.querySelector('[data-assignment-check]').click()`);
  await until(`Boolean(document.querySelector('.letter-results'))`);
  assert.match(await evaluate(`document.querySelector('.letter-results summary').textContent`),/15 из 15 верно/);
  await evaluate(`document.querySelector('.question').scrollIntoView({block:'start'})`);
  await screenshot('assigned-required-letters');
  await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
  assert(await evaluate(`document.documentElement.scrollWidth<=innerWidth+2`));
  await screenshot('assigned-required-letters-mobile');
  await send('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
  // Teacher can always close the long menu, and revoke without losing checked answers.
  await evaluate(`(async()=>{const d=await api('/api/login',{method:'POST',body:JSON.stringify({email:'teacher',password:'teacher123'})});state.user=d.user;state.token=d.token;localStorage.setItem('ege_token',d.token);await showAssignments()})()`);
  await until(`Boolean(document.querySelector('[data-revoke-test]'))`);
  assert(await evaluate(`(()=>{const b=document.querySelector('.learning-modal [data-close]'),r=b.getBoundingClientRect();return r.top>=0&&r.bottom<innerHeight&&b.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2))})()`));
  await evaluate(`document.querySelector('.learning-modal [data-content]').scrollTop=99999`);
  assert(await evaluate(`document.querySelector('.learning-modal [data-close]').getBoundingClientRect().top>=0`));
  await screenshot('assigned-menu-visible-close');
  await evaluate(`window.confirm=()=>true;document.querySelector('[data-revoke-test="${fixture.letter_test_id}"][data-student-id]').click()`);
  await until(`Boolean(document.querySelector('.learning-modal [data-content]')?.textContent.includes('Отозван'))`);
  const kept=await evaluate(`api('/api/assignments/results',{method:'POST',body:JSON.stringify({test_id:${JSON.stringify(fixture.letter_test_id)},student_id:${JSON.stringify(fixture.student_id)}})})`);
  assert.equal(kept.checked,1);assert(kept.revoked_at);
  await evaluate(`document.querySelector('.learning-modal [data-close]').click()`);
  await evaluate(`(async()=>{const d=await api('/api/login',{method:'POST',body:JSON.stringify({email:'student',password:'student123'})});state.user=d.user;state.token=d.token;localStorage.setItem('ege_token',d.token)})()`);
  const blocked=await evaluate(`api('/api/assignments/open',{method:'POST',body:JSON.stringify({test_id:${JSON.stringify(fixture.letter_test_id)}})}).then(()=>false,e=>e.code)`);
  assert.equal(blocked,'assignment_revoked');
  // A direct change of trainer must save a pupil's assignment draft first.
  await evaluate(`openAssignedTest(${JSON.stringify(fixture.test_id)})`);
  const questionId=await evaluate(`state.currentSession.questions[0].question_id`);
  await evaluate(`document.querySelector('#practiceView [data-answer]').click();document.querySelector('[data-platform-activity="ege12"]').click()`);
  await until(`state.currentActivity==='ege12'`);
  await evaluate(`openAssignedTest(${JSON.stringify(fixture.test_id)})`);
  assert(await evaluate(`Boolean(state.answers[${JSON.stringify(questionId)}])`));
  await evaluate(`document.querySelector('#practiceView [data-answer="2"]').click();[...document.querySelectorAll('#topActions button')].find(b=>b.textContent==='Кабинет').click()`);
  await until(`location.pathname==='/apps' && Boolean(document.querySelector('.catalog-page'))`);
  await evaluate(`openAssignedTest(${JSON.stringify(fixture.test_id)})`);
  assert(await evaluate(`lineDraft(${JSON.stringify(questionId)}).rows.includes('2')`));
  // Reloading the statistics URL must restore the page directly.
  await evaluate(`showOverallStatistics()`);await send('Page.reload');
  await until(`Boolean(document.querySelector('[data-own-history] .statistics-answer'))`);
  await send('Page.navigate',{url:'http://127.0.0.1:8098/games/participle-map/index.html'});
  await until(`typeof openLocation==='function' && typeof window.recordLearningGameAnswer==='function'`);await delay(350);
  await evaluate(`openLocation('identify');startIdentify('search');{const task=run.tasks[0].task;selected=new Set([task.tokens.findIndex((_,i)=>!task.correct.includes(i))]);checkIdentify()}`);
  await until(`fetch('/api/statistics/history?activity=game:participle-map&status=incorrect').then(r=>r.json()).then(d=>d.total>1)`);
  const mapAnswer=await evaluate(`fetch('/api/statistics/history?activity=game:participle-map&status=incorrect').then(r=>r.json()).then(d=>d.items.find(i=>i.question_id!=='qa-old-game'))`);
  assert(mapAnswer.given_answer && mapAnswer.correct_answer && !mapAnswer.prompt.startsWith('identify:'));
  await send('Page.navigate',{url:'http://127.0.0.1:8098/games/word-architecture/index.html'});
  await until(`Boolean(document.querySelector('[data-open="ending"]')) && typeof window.recordLearningGameAnswer==='function'`);await delay(350);
  await evaluate(`document.querySelector('[data-open="ending"]').click();document.querySelector('[data-action="start"]').click();document.querySelector('[data-special="none"]').click();document.querySelector('[data-action="check"]').click()`);
  await until(`fetch('/api/statistics/history?activity=game:word-architecture&status=incorrect').then(r=>r.json()).then(d=>d.total>0)`);
  const architectureAnswer=await evaluate(`fetch('/api/statistics/history?activity=game:word-architecture&status=incorrect').then(r=>r.json()).then(d=>d.items[0])`);
  assert(architectureAnswer.given_answer && architectureAnswer.correct_answer && !architectureAnswer.given_answer.includes('"ranges"'));
  assert.equal(errors.length,0,JSON.stringify(errors));
  fs.writeFileSync(path.join(qa,'statistics-check.json'),JSON.stringify({pass:true,navigation:10,historyTotal:total,summary:fixture.summary,errors},null,2));
  console.log('PASS: direct navigation, collapsed students, every activity, all pages, old errors, game details, full CSV, student view, draft saving, direct URL, mobile layout; no JS errors.');
 }finally{ws?.close();chrome.kill()}
})().catch(e=>{console.error(e);process.exitCode=1});
