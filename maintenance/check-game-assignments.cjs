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

  await evaluate(`renderTeacherGamesPage()`);
  await until(`Boolean(document.querySelector('[data-assign-cabinet-game="autumn-herbarium"]'))`);
  await screenshot('game-assignment-cabinet');
  await evaluate(`document.querySelector('[data-assign-cabinet-game="autumn-herbarium"]').click()`);
  await until(`Boolean(document.querySelector('[data-assign-game]'))`);
  await evaluate(`document.querySelector('[name=student][value="${fixture.student_id}"]').checked=true;document.querySelector('[data-game-target]').value='2';document.querySelector('[data-due-at]').value='2020-01-01T12:00';document.querySelector('[data-assign-game]').click()`);
  await until(`Boolean(document.querySelector('.learning-modal [data-content]')?.textContent.includes('Игра появилась'))`);
  const gameId=await evaluate(`api('/api/assignments').then(d=>d.games.find(g=>g.slug==='autumn-herbarium').id)`);
  await evaluate(`document.querySelector('.learning-modal [data-close]').click()`);
  await evaluate(`(async()=>{const d=await api('/api/login',{method:'POST',body:JSON.stringify({email:'student',password:'student123'})});state.user=d.user;state.token=d.token;localStorage.setItem('ege_token',d.token);await showStudentProfile()})()`);
  await until(`Boolean(document.querySelector('[data-launch-assigned-game]'))`);
  assert.match(await evaluate(`document.querySelector('.assigned-game-card').textContent`),/Полная версия игры/i);
  assert.match(await evaluate(`document.querySelector('.assigned-game-card').textContent`),/Просрочено/);
  await evaluate(`document.querySelector('.assigned-game-card').scrollIntoView({block:'center'})`);
  await screenshot('game-assignment-student');
  await evaluate(`document.querySelector('[data-launch-assigned-game]').click()`);
  try {await until(`Boolean(document.querySelector('.specimen')) && Boolean(document.querySelector('#roundSize [value="all"]'))`);} catch(err) {await screenshot('game-assignment-launch-error');console.log(await evaluate(`({url:location.href,text:document.body.innerText.slice(0,1200),errors:document.querySelector('[data-game-error]')?.textContent})`));throw err;}
  assert.equal(await evaluate(`new URLSearchParams(location.search).get('assignment_id')`),gameId);
  assert.equal(await evaluate(`Boolean(document.querySelector('.site-demo-ribbon'))`),false);
  assert(await evaluate(`JSON.parse(document.querySelector('#gameData').textContent).topics.some(t=>t.items.length>50)`));
  await until(`Boolean(document.querySelector('.specimen')) && typeof window.recordLearningGameAnswer==='function'`);
  await evaluate(`{const el=document.querySelector('.specimen'),data=JSON.parse(document.querySelector('#gameData').textContent),items=data.topics.flatMap(t=>t.items),item=items.find(x=>x.variant.replace(/[.]{2,}|…/g,' пропуск ')+'. Выберите пропущенную букву.'===el.getAttribute('aria-label'));if(!item)throw Error('Card not found');el.click();[...document.querySelectorAll('.basket')].find(b=>b.dataset.letter!==item.answer).click();el.click();[...document.querySelectorAll('.basket')].find(b=>b.dataset.letter===item.answer).click()}`);
  await until(`fetch('/api/assignments').then(r=>r.json()).then(d=>d.games.some(g=>g.id===${JSON.stringify(gameId)}&&g.checked===2&&g.correct===1&&g.completed_at))`);
  await screenshot('game-assignment-full-version');
  await send('Page.navigate',{url:'http://127.0.0.1:8098/apps/profile'});
  await until(`Boolean(document.querySelector('[data-card-status]'))`);
  await evaluate(`document.querySelector('[data-card-status]').value='completed';document.querySelector('[data-card-status]').dispatchEvent(new Event('change'))`);
  await until(`Boolean(document.querySelector('.assigned-game-card'))`);
  assert.match(await evaluate(`document.querySelector('.assigned-game-card').textContent`),/Решено: 2 из 2/);
  await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
  assert(await evaluate(`document.documentElement.scrollWidth<=innerWidth+2`));
  await evaluate(`document.querySelector('.assigned-game-card').scrollIntoView({block:'center'})`);
  await screenshot('game-assignment-mobile');
  await send('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
  await evaluate(`(async()=>{const d=await api('/api/login',{method:'POST',body:JSON.stringify({email:'teacher',password:'teacher123'})});state.user=d.user;state.token=d.token;localStorage.setItem('ege_token',d.token);await showAssignments()})()`);
  await until(`Boolean(document.querySelector('[data-revoke-assigned-game]'))`);
  assert.match(await evaluate(`document.querySelector('.assigned-game-card').textContent`),/верно: 1/);
  await evaluate(`window.confirm=()=>true;document.querySelector('[data-revoke-assigned-game]').click()`);
  await until(`Boolean(document.querySelector('.learning-modal .assigned-game-card')?.textContent.includes('Доступ отозван'))`);
  await evaluate(`(async()=>{const d=await api('/api/login',{method:'POST',body:JSON.stringify({email:'student',password:'student123'})});state.user=d.user;state.token=d.token;localStorage.setItem('ege_token',d.token)})()`);
  assert(await evaluate(`api('/api/assigned-games/open',{method:'POST',body:JSON.stringify({game_id:${JSON.stringify(gameId)}})}).then(()=>false,e=>e.code==='game_assignment_unavailable')`));
  assert.equal(errors.length,0,JSON.stringify(errors));
  fs.writeFileSync(path.join(qa,'game-assignments-check.json'),JSON.stringify({pass:true,paidFull:true,teacherAssignment:true,studentLaunch:true,realAnswers:2,revocation:true,errors},null,2));
  console.log('PASS: paid cabinet game, assignment form, student cabinet, full database without demo limits, 2 real answers, personal progress, deadline, mobile and revoke; no JS errors.');
 }finally{ws?.close();chrome.kill()}
})().catch(e=>{console.error(e);process.exitCode=1});
