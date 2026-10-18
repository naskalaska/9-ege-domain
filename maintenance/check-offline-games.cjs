const fs=require('node:fs'), path=require('node:path'), assert=require('node:assert/strict');
const {spawn}=require('node:child_process');
const {pathToFileURL,fileURLToPath}=require('node:url');
const root=path.resolve(__dirname,'..'),out=path.join(root,'HTML-игры — полные офлайн-версии'),qa=path.join(__dirname,'offline-qa');
const manifest=JSON.parse(fs.readFileSync(path.join(qa,'manifest.json'),'utf8'));
const selected=process.argv.slice(2), games=selected.length?manifest.filter(g=>selected.includes(g.slug)):manifest;
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const chrome=spawn('C:/Program Files/Google/Chrome/Application/chrome.exe',[
 '--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--autoplay-policy=no-user-gesture-required',
 '--remote-debugging-port=9236','--remote-allow-origins=*','--user-data-dir='+path.join(qa,'browser'),'about:blank'
],{windowsHide:true,stdio:'ignore'});

const actions={
 'oh-yo': `state.level=4;state.mode=1;start();answer(current().answer==='о'?'е':'о');if(state.session.wrong!==1)throw Error('Wrong answer was not recorded');next();answer(current().answer);if(state.session.correct!==1)throw Error('Correct answer was not recorded');showMemo('root');`,
 'autumn-leaves': `startGame();openQuestion(leaves[0]);checkAnswer(active.q.answer);`,
 'autumn-herbarium': `document.querySelector('#newBtn').click();document.querySelector('.specimen').click();document.querySelector('.basket').click();document.querySelector('#settingsBtn').click();if(!document.querySelector('#settingsDialog').open)throw Error('Offline full settings unavailable');`, 
 'suffixes-nouns': `startGame();document.querySelector('.item').click();{const q=gameQuestions[currentQuestionIndex];checkAnswer(q.correct,document.querySelectorAll('.answer-option')[q.correct]);}`,
 'homogeneous-members-magic': `document.querySelector('#startButton').click();handleAnswer(scrollButtons.find(b=>normalize(b.dataset.answer)===normalize(gameTasks[currentIndex].correct)));`,
 'berry-season-ik-ek': `{const fruit=document.querySelector('.fruit');fruit.click();document.querySelector('.basket[data-letter="'+fruit.dataset.answer+'"]').click();}`,
 'paronyms': `(async()=>{document.querySelector('#startButton').click();for(let n=0;n<45;n++)document.querySelector('#resetButton').click();if(!document.querySelector('#demoLimit').classList.contains('hidden'))throw Error('Demo blocked full game');let cards=[...document.querySelectorAll('.picture-card')];for(const card of cards){[...document.querySelectorAll('[data-word]')].find(b=>b.dataset.word===card.dataset.target).click();card.click()}document.querySelector('#checkButton').click();if(!document.querySelector('#message').textContent.includes('Верно'))throw Error('Paronym answer check');document.querySelector('#nextButton').click();await new Promise(r=>setTimeout(r,1200));cards=[...document.querySelectorAll('.picture-card')];for(let n=0;n<cards.length;n++){const word=cards[(n+1)%cards.length].dataset.target;[...document.querySelectorAll('[data-word]')].find(b=>b.dataset.word===word).click();cards[n].click()}document.querySelector('#checkButton').click();await new Promise(r=>setTimeout(r,1800));if(!document.querySelector('#explanationImage').getAttribute('src').startsWith('Памятки теории/'))throw Error('Explanation is not external theory')})()`,
 'numerals-hit-parade': `openStage(0);openMemo();`,
 'karaoke-numerals': `document.querySelector('[data-screen="reading"]').click();document.querySelector('[data-screen="theory"]').click();document.querySelector('[data-model-next]')?.click();`,
 'summer-gerund-bar': `renderLesson(0);checkLessonTask(0,lessonTasks[0][0],lessonTasks[0][0].answer);`,
 'mouse-space': `startGame();answer(state.currentOptions.left.correct?'left':'right');`,
 'verb-conjugation-quest': `startGame();answerAlgorithmQuestion(ALGORITHM_QUESTIONS[0].correct);`,
 'truth-action-oge': `if(DEMO_MODE)throw Error('Demo mode active');document.querySelector('#playerName').value='Проверка 1';addPlayer({preventDefault(){}});document.querySelector('#playerName').value='Проверка 2';addPlayer({preventDefault(){}});startGame();for(let n=0;n<25;n++){openTaskCard(state.players[state.currentIndex],'truth');completeCard('done')}if(state.players.reduce((n,p)=>n+p.score,0)!==25)throw Error('Full game did not allow 25 turns');`,
 'grammar-zoo': `document.querySelector('[data-subtopic]')?.click();`,
 'parts-of-speech-kingdom': `if(DEMO_MODE||CARDS_PER_CATEGORY!==10)throw Error('Demo round size');{const card=currentCard();attemptPlace(card.cat);if(placed!==1)throw Error('Answer check failed');openMemo(currentMode.cats[0]);}`,
 'butterflies-participial-phrase': `[...document.querySelectorAll('button')].find(b=>b.textContent.includes('Войти в оранжерею')).click();`,
 'butterflies-participle-suffixes': `document.querySelector('[data-start]').click();document.querySelector('[data-i]').click();document.querySelector('.letterInput').value=items[current].answer;document.querySelector('[data-check]').click();if(!done.has(current))throw Error('Constructor did not accept correct answer');`,
 'orthoshooting': `document.querySelector('[data-cat]')?.click();`,
 'expedition-memory-isolated-members': `document.querySelector('#startBtn')?.click();toggleTheory();`,
 'syntactic-soup': `document.querySelector('#rulesButton').click();`,
 'foxwarts-syntax': `openHelp();`,
 'participle-map': `openLocation('identify');`,
 'word-architecture': `document.querySelector('[data-open="ending"], [data-section-open="ending"], [data-route="ending"], [data-go="ending"]')?.click();document.querySelector('[data-memo]')?.click();`,
 'palace-restoration': `document.querySelector('[data-game-begin]')?.click();`,
 'fluffs': `startGame();document.querySelector('.item').click();{const q=gameQuestions[currentQuestionIndex];checkAnswer(q.correct,document.querySelectorAll('.answer-option')[q.correct]);}`,
};

(async()=>{
 let ws;
 const results=[];
 try{
  let tabs;
  for(let n=0;n<60;n++){try{tabs=await(await fetch('http://127.0.0.1:9236/json')).json();break}catch{await delay(200)}}
  if(!tabs)throw Error('Chrome did not start');
  ws=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl);await new Promise(resolve=>ws.onopen=resolve);
  let id=0,current=null;
  const pending=new Map();
  const send=(method,params={})=>new Promise((resolve,reject)=>{const callId=++id;const timer=setTimeout(()=>{pending.delete(callId);reject(Error('CDP timeout '+method))},90000);pending.set(callId,{resolve,reject,timer});ws.send(JSON.stringify({id:callId,method,params}));});
  ws.onmessage=event=>{
   const msg=JSON.parse(event.data);
   if(msg.id){const item=pending.get(msg.id);if(item){clearTimeout(item.timer);pending.delete(msg.id);msg.error?item.reject(Error(JSON.stringify(msg.error))):item.resolve(msg.result);}return;}
   if(msg.method==='Runtime.exceptionThrown'&&current){const e=msg.params.exceptionDetails;current.errors.push((e.exception?.description||e.text).slice(0,1200));}
   if(msg.method==='Fetch.requestPaused'){
    const {requestId,request}=msg.params;
    let allow=false;
    if(request.url.startsWith('file:')){
     const filename=fileURLToPath(request.url);allow=filename.startsWith(out+path.sep)&&(filename.endsWith('Игра.html')||filename.endsWith('Открыть игры.html')||filename.includes(path.sep+'Памятки теории'+path.sep));
    }
    if(!allow&&current)current.badRequests.push(request.url.slice(0,500));
    send(allow?'Fetch.continueRequest':'Fetch.failRequest',allow?{requestId}:{requestId,errorReason:'InternetDisconnected'}).catch(()=>{});
   }
  };
  const evaluate=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value;};
  await send('Runtime.enable');await send('Page.enable');
  await send('Fetch.enable',{patterns:[{urlPattern:'http://*'},{urlPattern:'https://*'},{urlPattern:'file://*'}]});
  await send('Emulation.setDeviceMetricsOverride',{width:1365,height:900,deviceScaleFactor:1,mobile:false});
  for(const game of games){
   current={slug:game.slug,errors:[],badRequests:[]};results.push(current);
   try{
    await send('Page.navigate',{url:pathToFileURL(path.join(out,game.html)).href});
    let ready=false;
    for(let n=0;n<100;n++){try{ready=await evaluate('Boolean(window.__OFFLINE_READY)')}catch{}if(ready)break;await delay(150)}
    assert(ready,'Offline page did not finish loading');await delay(300);
    current.initial=await evaluate(`({title:document.title,charset:document.characterSet,body:document.body.innerText.length,scripts:[...document.scripts].filter(s=>s.src).length,styles:document.querySelectorAll('link[rel=stylesheet]').length,flags:window.__OFFLINE_FULL_CHECKS,missing:[...window.__OFFLINE_MISSING_RESOURCES]})`);
    assert.equal(current.initial.charset,'UTF-8','Encoding of the offline file');
    assert(current.initial.body>40,'Empty game UI');assert.equal(current.initial.scripts,0);assert.equal(current.initial.styles,0);
    assert(current.initial.flags.every(([name,value])=>value===false),'A demo flag is enabled');
    try{await evaluate(actions[game.slug]||'true');current.interaction='passed'}catch(error){current.interaction='FAILED: '+error.message;}
    await delay(400);
    current.after=await evaluate(`({missing:[...window.__OFFLINE_MISSING_RESOURCES],broken:[...document.images].filter(i=>i.getClientRects().length&&i.complete&&!i.naturalWidth&&i.getAttribute('src')).map(i=>i.getAttribute('src').slice(0,180)),body:document.body.innerText.slice(0,180)})`);
    const shot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});fs.writeFileSync(path.join(qa,game.slug+'.png'),Buffer.from(shot.data,'base64'));
    // Decode every embedded and external image, including cards not visible in the first round.
    current.imageAudit=await evaluate(`(async()=>{const entries=Object.entries(window.__OFFLINE_ASSETS).filter(([key,src])=>/\\.(png|jpe?g|webp|svg|gif)$/i.test(key));const extra=(window.__OFFLINE_BUNDLE_INFO.theory||[]).map(t=>[t.file,t.file]);const unique=[...new Map([...entries,...extra].map(e=>[e[1],e])).values()];let passed=0;const failed=[];for(let start=0;start<unique.length;start+=4){await Promise.all(unique.slice(start,start+4).map(async([name,src])=>{const image=new Image();image.src=src;try{await image.decode();if(!image.naturalWidth)throw Error();passed++}catch{failed.push(name)}}))}return{passed,failed}})()`);
   }catch(error){current.fatal=error.message;}
   current.pass=!current.fatal&&!current.errors.length&&!current.badRequests.length&&current.after&&!current.after.missing.length&&!current.after.broken.length&&!current.imageAudit?.failed.length&&current.interaction==='passed';
   fs.writeFileSync(path.join(qa,selected.length?'browser-check-selected.json':'browser-check.json'),JSON.stringify(results,null,2));
   console.log(game.slug,current.pass?'PASS':'FAIL',JSON.stringify({fatal:current.fatal,interaction:current.interaction,errors:current.errors,requests:current.badRequests,missing:current.after?.missing,broken:current.after?.broken,images:current.imageAudit}));
   current=null;await send('Page.navigate',{url:'about:blank'});await send('HeapProfiler.collectGarbage').catch(()=>{});
  }
  console.log('Games checked',results.length,'passed',results.filter(r=>r.pass).length);
  if(results.some(r=>!r.pass))process.exitCode=1;
 }finally{ws?.close();chrome.kill();}
})().catch(error=>{console.error(error);chrome.kill();process.exitCode=1;});
