const fs = require('node:fs'), path = require('node:path'), assert = require('node:assert/strict');
const {spawn} = require('node:child_process');
const qa = path.join(__dirname, 'offline-qa');
fs.mkdirSync(qa, {recursive:true});
const delay = ms => new Promise(r => setTimeout(r, ms));
const python = 'C:/Users/anast/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
const fixtureServer = spawn(python, [path.join(__dirname, 'serve-statistics-qa.py')], {cwd:path.join(__dirname,'..'), env:{...process.env, QA_PORT:'8119'}, windowsHide:true, stdio:['ignore','pipe','pipe']});
fixtureServer.stdout.on('data', data=>process.stdout.write(data));
fixtureServer.stderr.on('data', data=>process.stderr.write(data));
const chrome = spawn('C:/Program Files/Google/Chrome/Application/chrome.exe', [
  '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
  '--remote-debugging-port=9243', '--remote-allow-origins=*',
  '--user-data-dir='+path.join(qa, 'espresso-browser'), 'about:blank'
], {windowsHide:true, stdio:'ignore'});
(async () => {
  let ws;
  try {
    let tabs;
    for(let i=0;i<60;i++){try{tabs=await(await fetch('http://127.0.0.1:9243/json')).json();break;}catch{await delay(200);}}
    assert(tabs, 'Chrome did not start');
    ws = new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl);
    await new Promise(r=>ws.onopen=r);
    let seq=0; const pending=new Map(), errors=[];
    ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(Error(JSON.stringify(m.error))):p.resolve(m.result);}else if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails);};
    const send=(method,params={})=>new Promise((resolve,reject)=>{const id=++seq;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));});
    const evaluate=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||JSON.stringify(r.exceptionDetails));return r.result.value;};
    const until=async expression=>{for(let i=0;i<150;i++){if(await evaluate(expression))return;await delay(100);}throw Error('Timeout: '+expression);};
    const navigate=async route=>{await send('Page.navigate',{url:'http://127.0.0.1:8119'+route});};
    const screenshot=async name=>{const shot=await send('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(qa,name+'.png'),Buffer.from(shot.data,'base64'));};
    await send('Runtime.enable'); await send('Page.enable');
    await send('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
    for(let i=0;i<60;i++){try{const r=await fetch('http://127.0.0.1:8119/login');if(r.ok)break;}catch{}await delay(200);}
    await navigate('/login'); await until(`typeof api==='function'`);
    await evaluate(`(async()=>{const d=await api('/api/login',{method:'POST',body:JSON.stringify({email:'teacher',password:'teacher123'})});state.user=d.user;state.token=d.token;localStorage.setItem('ege_token',d.token);await loadActivity('ege9')})()`);
    assert.equal(await evaluate(`Boolean(document.querySelector('[data-task-statistics]'))`), true);
    assert.equal(await evaluate(`document.querySelectorAll('.statistics-quick-students, [data-quick-student]').length`), 0);
    await screenshot('espresso-teacher-buttons');
    await evaluate(`document.querySelector('[data-task-statistics]').click()`);
    await until(`Boolean(document.querySelector('.statistics-metrics'))`);
    assert.equal(await evaluate(`new URLSearchParams(location.search).get('activity')`), 'ege9');
    assert.equal(await evaluate(`document.querySelector('.statistics-class tbody').rows.length`), 1);
    await evaluate(`document.querySelector('.statistics-student').open=true`);
    await until(`Boolean(document.querySelector('[data-student-history] form'))`);
    assert.deepEqual(await evaluate(`(()=>{const e=document.querySelector('[data-student-history] select[name=activity]');return [e.value,e.disabled]})()`), ['ege9',true]);
    await send('Page.reload');
    await until(`Boolean(document.querySelector('.statistics-class tbody'))`);
    assert.equal(await evaluate(`document.querySelector('.statistics-class tbody').rows.length`), 1);
    await evaluate(`showProgress()`); await until(`Boolean(document.querySelector('.statistics-class tbody'))`);
    assert(await evaluate(`document.querySelector('.statistics-class tbody').rows.length>1`));
    await navigate('/shop'); await until(`Boolean(document.querySelector('[data-shop-rubric="speech"]'))`);
    await evaluate(`document.querySelector('[data-shop-rubric="speech"]').click()`);
    assert.equal(await evaluate(`(()=>{const c=[...document.querySelectorAll('[data-shop-card]')].find(c=>c.textContent.includes('Убийство за ихний экспрессо'));return Boolean(c && !c.classList.contains('shop-filtered-out') && c.textContent.includes('300 ₽'))})()`),true);
    await navigate('/games/espresso-murder/index.html');
    await until(`typeof openSection==='function' && Boolean(document.querySelector('#app h1'))`);
    assert.equal(await evaluate(`document.querySelectorAll('[data-start-pack]').length`),0);
    await evaluate(`openSection(0)`);
    assert(await evaluate(`document.querySelector('#app').textContent.length>100`));
    await screenshot('espresso-public-game');
    await navigate('/Full-94602718350964-espresso-murder/index.html');
    await until(`document.querySelectorAll('[data-start-pack]').length===5`);
    assert.equal(await evaluate(`FIXED_DECKS.length`), 7);
    assert(await evaluate(`FIXED_DECKS.every(section=>section.length===5)`));
    await evaluate(`document.querySelector('[data-start-pack="4"]').click()`);
    assert.equal(await evaluate(`state.currentPack`),4);
    await evaluate(`openSection(0)`);
    assert(await evaluate(`document.querySelector('#app').textContent.length>100`));
    await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
    await screenshot('espresso-full-game-mobile');
    assert.equal(errors.length,0,JSON.stringify(errors));
    fs.writeFileSync(path.join(qa,'espresso-statistics-check.json'),JSON.stringify({pass:true,errors},null,2));
    console.log('PASS: teacher buttons, scoped statistics and reload, all students, shop category and price, public game, five full packs, pack selection, mobile render; no JS errors.');
  } finally {ws?.close();chrome.kill();try{await fetch('http://127.0.0.1:8119/qa/shutdown',{method:'POST'});}catch{}fixtureServer.kill();}
})().catch(e=>{console.error(e);process.exitCode=1;});
