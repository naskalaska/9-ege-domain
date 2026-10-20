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

  await evaluate(`showStudentProfile(${JSON.stringify(fixture.student_id)})`);
  await until(`Boolean(document.querySelector('[data-card-history] [data-repeat-error]'))`);
  assert.match(await evaluate(`document.body.innerText`),/Единая карточка ученика/i);
  assert.equal(await evaluate(`document.querySelectorAll('.student-workspace meter').length`),8);
  await screenshot('student-card-teacher');
  await evaluate(`document.querySelector('[data-work-deadline="${fixture.test_id}"]').click()`);
  await evaluate(`document.querySelector('[data-due-at]').value='2020-01-01T12:00';document.querySelector('[data-save-deadline]').click()`);
  await until(`Boolean(document.querySelector('[data-card-tests]')?.textContent.includes('Просрочен'))`);
  assert.equal(await evaluate(`document.querySelectorAll('.learning-backdrop').length`),0);
  await evaluate(`document.querySelector('[data-card-history] [data-repeat-error]').click()`);
  await until(`Boolean(document.querySelector('[data-repeat-confirm]'))`);
  await evaluate(`document.querySelector('[data-due-at]').value='2020-01-02T12:00';document.querySelector('[data-repeat-confirm]').click()`);
  await until(`Boolean(document.querySelector('.learning-modal [data-content]')?.textContent.includes('Повторение назначено'))`);
  const repeatId=await evaluate(`api('/api/assignments').then(d=>d.tests.find(t=>t.title.startsWith('Повторение ошибки')).id)`);
  await evaluate(`document.querySelector('.learning-modal [data-close]').click();showAssignmentCalendar(${JSON.stringify(fixture.student_id)})`);
  await until(`document.querySelectorAll('[data-calendar-day]').length>27`);
  assert.match(await evaluate(`document.querySelector('[data-calendar-overdue]').textContent`),/Повторение ошибки/);
  await screenshot('calendar-teacher');
  await send('Page.reload');
  await until(`document.querySelectorAll('[data-calendar-day]').length>27`);
  await evaluate(`document.querySelector('[data-month-prev]').click();document.querySelector('[data-month-next]').click();document.querySelector('[data-calendar-day]').click()`);
  assert.match(await evaluate(`document.querySelector('[data-calendar-work] h3').textContent`),/Работы на/);
  await evaluate(`(async()=>{const d=await api('/api/login',{method:'POST',body:JSON.stringify({email:'student',password:'student123'})});state.user=d.user;state.token=d.token;localStorage.setItem('ege_token',d.token);await showStudentProfile()})()`);
  await until(`Boolean(document.querySelector('[data-card-history] [data-repeat-error]'))`);
  assert.match(await evaluate(`document.querySelector('[data-card-tests]').textContent`),/Просрочен/);
  const sourceAttempt=await evaluate(`document.querySelector('[data-card-history] [data-repeat-error]').dataset.repeatError`);
  await evaluate(`document.querySelector('[data-card-history] [data-repeat-error]').click();document.querySelector('[data-repeat-confirm]').click()`);
  await until(`Boolean(state.currentSession?.assignment_id && document.querySelector('[data-assignment-check]'))`);
  assert.equal(await evaluate(`state.currentSession.assignment_id`),repeatId);
  // The expired repeat is still solvable, and its frozen answer key matches the source.
  await evaluate(`for(const row of ${JSON.stringify(fixture.row_key)}) document.querySelector('[data-answer="'+row+'"]').click();document.querySelector('[data-assignment-check]').click()`);
  await until(`Boolean(document.querySelector('.result-item.ok'))`);
  await evaluate(`showStudentProfile()`);
  await until(`Boolean(document.querySelector('[data-card-history] [data-repeat-error]'))`);
  assert.equal(await evaluate(`document.querySelector('[data-card-history] [data-repeat-error]').dataset.repeatError`),sourceAttempt);
  assert.match(await evaluate(`document.body.innerText`),/К выполнению/);
  await screenshot('student-card-student');
  await send('Page.reload');
  await until(`Boolean(document.querySelector('[data-card-history] [data-repeat-error]'))`);
  await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
  assert(await evaluate(`document.documentElement.scrollWidth<=innerWidth+2`));
  await screenshot('student-card-mobile');
  await evaluate(`showAssignmentCalendar()`);
  await until(`document.querySelectorAll('[data-calendar-day]').length>27`);
  assert(await evaluate(`document.documentElement.scrollWidth<=innerWidth+2`));
  await screenshot('calendar-mobile');
  await evaluate(`document.querySelector('[data-calendar-overdue] [data-work-open]').click()`);
  await until(`Boolean(document.querySelector('[data-assignment-check]'))`);
  assert.equal(await evaluate(`state.currentSession.assignment_id`),fixture.test_id);
  const forbidden=await evaluate(`api('/api/assignments/deadline',{method:'POST',body:JSON.stringify({test_id:${JSON.stringify(fixture.test_id)},due_at:null})}).then(()=>false,e=>true)`);
  assert.equal(forbidden,true);
  assert.equal(errors.length,0,JSON.stringify(errors));
  fs.writeFileSync(path.join(qa,'student-workspace-check.json'),JSON.stringify({pass:true,profile:true,calendar:true,deadlines:true,lateSolving:true,repeat:true,errors},null,2));
  console.log('PASS: teacher/student cards, deadlines, calendar, repeat from error, late solving, persistence, permissions, mobile; no JS errors.');
 }finally{ws?.close();chrome.kill()}
})().catch(e=>{console.error(e);process.exitCode=1});
