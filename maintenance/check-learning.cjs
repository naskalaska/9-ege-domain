const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {spawn} = require('node:child_process');
const root = path.resolve(__dirname,'..');
const delay = ms => new Promise(resolve=>setTimeout(resolve,ms));
const chrome = spawn('C:/Program Files/Google/Chrome/Application/chrome.exe',[
  '--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check',
  '--remote-debugging-port=9231','--remote-allow-origins=*',
  '--user-data-dir='+path.join(root,'maintenance/learning-browser'),'about:blank'
],{windowsHide:true,stdio:'ignore'});
(async()=>{
 let ws;
 try {
  let tabs;
  for(let n=0;n<50;n++) {try {tabs=await(await fetch('http://127.0.0.1:9231/json')).json();break;}catch {await delay(200);}}
  if(!tabs) throw Error('Chrome did not start');
  ws=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl);
  await new Promise(resolve=>ws.onopen=resolve);
  let id=0;const pending=new Map();const errors=[];
  ws.onmessage=event=>{const msg=JSON.parse(event.data);if(msg.id){pending.get(msg.id)?.(msg);pending.delete(msg.id);}if(msg.method==='Runtime.exceptionThrown') errors.push(msg.params.exceptionDetails);};
  const send=(method,params={})=>new Promise(resolve=>{pending.set(++id,resolve);ws.send(JSON.stringify({id,method,params}));});
  const evaluate=async expression=>{const response=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(response.result.exceptionDetails)throw Error(JSON.stringify(response.result.exceptionDetails));return response.result.result.value;};
  await send('Runtime.enable');await send('Page.enable');
  await send('Page.navigate',{url:'http://127.0.0.1:8097/login'});await delay(1000);
  await evaluate(`(async()=>{const d=await api('/api/login',{method:'POST',body:JSON.stringify({email:'teacher',password:'teacher123'})});state.user=d.user;state.token=d.token;localStorage.setItem('ege_token',d.token);await loadActivity('ege9');showTestComposer();})()`);
  assert.equal(await evaluate(`document.querySelectorAll('[data-assign-composed]').length`),1);
  await evaluate(`document.querySelector('#testCount').value='2';document.querySelector('[data-assign-composed]').click()`);await delay(350);
  await evaluate(`(()=>{const m=[...document.querySelectorAll('.modal-backdrop')].at(-1);m.querySelector('[name=student]').checked=true;m.querySelector('[data-title]').value='Браузер: смешанные корни';m.querySelector('[data-assign]').click()})()`);await delay(500);
  assert.match(await evaluate(`document.body.innerText`),/Тест из 2 вопросов назначен/);
  await evaluate(`document.querySelectorAll('.modal-backdrop').forEach(m=>m.remove());showAssignments()`);await delay(250);
  assert.match(await evaluate(`document.body.innerText`),/Браузер: смешанные корни/);
  await evaluate(`(async()=>{document.querySelectorAll('.modal-backdrop').forEach(m=>m.remove());const d=await api('/api/login',{method:'POST',body:JSON.stringify({email:'student',password:'student123'})});state.user=d.user;state.token=d.token;localStorage.setItem('ege_token',d.token);state.currentActivity=null;renderDashboard();await refreshAssignmentButton();await showAssignments()})()`);
  assert.equal(await evaluate(`Boolean(document.querySelector('#assignmentNotice'))`),true);
  await evaluate(`document.querySelector('[data-open-test]').click()`);await delay(350);
  assert.equal(await evaluate(`document.querySelectorAll('#practiceView .question').length`),2);
  await evaluate(`document.querySelectorAll('#practiceView .question').forEach(q=>q.querySelector('[data-answer]').click())`);await delay(650);
  await evaluate(`document.querySelector('[data-exit-assignment]').click()`);await delay(250);
  await evaluate(`document.querySelector('[data-open-test]').click()`);await delay(250);
  assert.equal(await evaluate(`Object.keys(state.answers).length`),2);
  await evaluate(`document.querySelector('#submitPractice').click()`);await delay(350);
  assert.equal(await evaluate(`Boolean(state.currentSession.result)`),true);
  const shot=await send('Page.captureScreenshot',{format:'png'});
  fs.writeFileSync(path.join(root,'maintenance/learning-results.png'),Buffer.from(shot.result.data,'base64'));
  // Check a real game's answer event travels through the authenticated API.
  await send('Page.navigate',{url:'http://127.0.0.1:8097/games/suffixes-nouns/index.html'});await delay(700);
  await evaluate(`startGame();document.querySelector('.item').click();checkAnswer(gameQuestions[currentQuestionIndex].correct,document.querySelector('.answer-option'))`);await delay(350);
  const games=await evaluate(`fetch('/api/progress').then(r=>r.json()).then(d=>d.by_game)`);
  assert.equal(games[0].total,1);assert.equal(games[0].correct,1);
  assert.equal(errors.length,0,JSON.stringify(errors));
  console.log('PASS: composer, assignment, notification, resume, completion and real game answer; no browser errors.');
 } finally {ws?.close();chrome.kill();}
})().catch(error=>{console.error(error);process.exitCode=1;});
