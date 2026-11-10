const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const bank=JSON.parse(fs.readFileSync(path.join(__dirname,'..','task_1_3_trainer_bank.json'),'utf8'));
// DOM-independent runtime checks use the actual app and assignment handlers.
function element(){const children=new Map(),listeners={};return {value:'',checked:false,dataset:{},style:{},innerHTML:'',textContent:'',disabled:false,isConnected:true,children,listeners,
  classList:{add(){},remove(){},toggle(){}},setAttribute(){},append(){},remove(){},focus(){},
  addEventListener(type,fn){listeners[type]=fn;},
  querySelector(selector){if(!children.has(selector))children.set(selector,element());return children.get(selector);},
  querySelectorAll(){return [];},insertAdjacentHTML(_,html){this.innerHTML+=html;},
};}
const root=element();const document={querySelector:s=>root.querySelector(s),querySelectorAll:()=>[],createElement:element,addEventListener(){},body:element()};
const context=vm.createContext({document,console,window:{location:{pathname:'/apps/ege1-3'},addEventListener(){},scrollTo(){}},history:{pushState(){},replaceState(){}},localStorage:{getItem(){return null;}},URL,setTimeout(){},clearTimeout(){},setInterval(){},clearInterval(){},alert(){},confirm(){return true;}});
const run=s=>vm.runInContext(s,context);
for(const file of ['learning.js','text-lab.js','speech.js','app.js']){
  let code=fs.readFileSync(path.join(__dirname,'static',file),'utf8');
  if(file==='app.js')code=code.replace(/\nstartHeartbeat\(\);\s*restoreSession\(\);\s*$/,'');
  run(code);
}
async function main(){
  const rules={'Задание 1':[{rule_id:'gap-topic',rule_name:'Местоимения',category:'Задание 1',count:27}], 'Задание 2':[], 'Задание 3':[{rule_id:'style-topic',rule_name:'Художественный',category:'Задание 3',count:20}]};
  context.bootstrap={rules,word_count:86,activities:[],category_progress:{}};
  context.requests=[];
  run(`api=async (url,options)=>{requests.push({url,options});return bootstrap;};renderDashboard=()=>{};state.user={role:'student'};`);
  await run(`loadActivity('ege1-3')`);
  assert.equal(run('state.currentActivity'),'ege1-3');assert.equal(run('state.mode'),'gap');
  assert.equal(run('activityFromPath()'),'ege1-3');assert.equal(run('activityMeta["ege1-3"].shortTitle'),'Задания 1–3');
  assert.equal(run('Object.keys(activityModes()).length'),6);
  assert.equal(run('formatTestAnswer(["таков","таким"],{kind:"text_lab_gap"})'),'таков / таким');
  assert.equal(run('formatTestAnswer("false",{kind:"text_lab_bool"})'),'Неверно');
  run('renderSetup()');assert(document.querySelector('#setupView').innerHTML.includes('Часть речи'));
  run('state.mode="characteristics";renderSetup()');assert(document.querySelector('#setupView').innerHTML.includes('Стиль речи'));
  run('state.mode="exam";renderSetup()');assert(document.querySelector('#setupView').innerHTML.includes('по 3 задания'));
  // The UI joins PDF line breaks, retains paragraphs and marks original offsets.
  const e=bank[47];context.question={question_id:'q',kind:'text_lab_bool',task_number:2,text:e.text,highlight_ranges:[e.tasks['2'].options[0].range],statement:e.tasks['2'].options[0].text,prompt:'Совпадает ли значение?',options:[]};
  const html=run('textLabContext(question)');assert(!html.includes('\n'));assert(html.includes('в своих чистых и строгих очертаниях'));
  const [a,b]=context.question.highlight_ranges[0];assert(html.includes('<mark>'+e.text.slice(a,b)+'</mark>'));
  run('state.answers={};state.currentActivity="ege1-3"');
  assert(run('renderQuestion(question,0)').includes('data-answer="false"'));
  assert(run('renderQuestion(question,0)').includes('Тексты из сборников Р.А. Дощинского 2025, 2026 года'));
  assert.equal(run('answerIsComplete(question)'),false);run('state.answers.q="false"');assert.equal(run('answerIsComplete(question)'),true);
  context.multi={...context.question,question_id:'m',kind:'text_lab_multi',task_number:3,highlight_ranges:[],options:bank[0].tasks['3'].options.map(o=>({n:o.n,text:o.text}))};
  assert.equal((run('renderQuestion(multi,0)').match(/type="checkbox"/g)||[]).length,5);
  for(const answer of ['',{},'123456','1x']){context.answer=answer;run('state.answers.m=answer');assert.equal(run('answerIsComplete(multi)'),false);}
  run('state.answers.m="235"');assert.equal(run('answerIsComplete(multi)'),true);
  // The same input handlers write full words and multiple selections to shared assignment drafts.
  const free=element(),checkbox=element();free.dataset.textLabFree='g';free.value='потому что';checkbox.dataset={questionId:'m',textLabChoice:'4'};checkbox.checked=true;
  context.inputRoot={querySelectorAll:s=>s==='[data-text-lab-free]'?[free]:s==='[data-text-lab-choice]'?[checkbox]:[]};
  run('bindTextLabAnswers(inputRoot)');free.listeners.input();checkbox.listeners.change();
  assert.equal(run('state.answers.g'),'потому что');assert.equal(run('state.answers.m'),'2345');
  checkbox.checked=false;checkbox.listeners.change();assert.equal(run('state.answers.m'),'235');
  // Topic state from another mode cannot be sent to the server accidentally.
  context.composer=element();context.composer.querySelector('#testMode').value='characteristics';context.composer.querySelector('#testCount').value='7';context.composer.querySelectorAll=()=>[{checked:true,dataset:{topicId:'style-topic'}},{checked:true,dataset:{topicId:'second-style'}}];context.composer.querySelector('#testIncludeErrors').checked=true;
  const config=run('collectTextLabTestConfig(composer)');assert.equal(config.activity,'ege1-3');assert.equal(config.mode,'characteristics');assert.equal(config.count,7);assert.deepEqual(Array.from(config.rule_ids),['style-topic','second-style']);assert.equal(config.include_errors,true);
  // Starting from the native app passes the selected rubric and switches to native practice.
  context.started={session_id:'s',mode:'gap',questions:[{...context.question,kind:'text_lab_gap',task_number:1}]};
  run('api=async (url,options)=>{requests.push({url,options});return started;};state.mode="gap";state.textLabTopics={gap:["gap-topic","second-topic"]};state.questionCount=5;');
  await run('startPractice()');const req=context.requests.at(-1);assert.equal(req.url,'/api/apps/ege1-3/practice/start');assert.deepEqual(JSON.parse(req.options.body).rule_ids,['gap-topic','second-topic']);
  assert.equal(run('state.currentSession.session_id'),'s');assert(document.querySelector('#practiceView').innerHTML.includes('data-text-lab-free'));
  // A completed question displays feedback and is not offered for checking twice.
  run('state.currentSession.checked_results={q:{is_correct:true,given_answer:"потому что",correct_answer:"потому что",explanation:"Связь"}};renderTextLabPractice()');
  assert(!document.querySelector('#practiceView').innerHTML.includes('data-text-lab-check'));
  // Composer downloads use the real POST helper contract, including selected topic.
  let appended;document.body.append=el=>{appended=el;};
  run('state.user={role:"teacher"};state.mode="gap";downloadRequest=async (...args)=>{requests.push(args);};showTextLabTestComposer()');
  appended.querySelector('#testCount').value='2';appended.querySelector('[data-text-lab-topic]').value='gap-topic';
  const download=appended.querySelector('#downloadTest');await download.onclick({target:download});const request=context.requests.at(-1);
  assert.equal(request[0],'/api/teacher/test');assert.equal(request[2].method,'POST');assert.equal(JSON.parse(request[2].body).activity,'ege1-3');
  run('api=async()=>({students:[],groups:[],tests:[],games:[]});function assignedGameCard(){return "";}function bindAssignedGames(){}');
  await run('showAssignments()');
  assert(appended.querySelector('[data-content]').innerHTML.includes('<option value="ege1-3">Задания 1–3</option>'));
  assert(!appended.querySelector('[data-content]').innerHTML.includes('<option value="html-games">'));
  const index=fs.readFileSync(path.join(__dirname,'static/index.html'),'utf8');assert(index.indexOf('/text-lab.js')<index.indexOf('/app.js'));
  console.log('Text-lab runtime passed: native route/setup, six modes, paragraph flow and highlights, full choices, shared answer handlers, server payloads, feedback, composer POST and script order.');
}
main().catch(err=>{console.error(err);process.exitCode=1;});
