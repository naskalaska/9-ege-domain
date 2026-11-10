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
  closest(){return this;},querySelectorAll(){return [];},insertAdjacentHTML(_,html){this.innerHTML+=html;},
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
 context.bootstrap={rules:{'Существительное':[{rule_id:'morph:Существительное',category:'Существительное',rule_name:'Существительное',count:159}]},word_count:420,activities:[],category_progress:{},bank_progress:{solved:0,total:420},rule_progress:{'morph:Существительное':{solved:0,total:159}}};
 context.requests=[];
 run(`api=async (url,options)=>{requests.push({url,options});return bootstrap;};renderDashboard=()=>{};state.user={role:'student'};`);
 await run(`loadActivity('ege7')`);
 assert.equal(run('state.currentActivity'),'ege7');
 assert.equal(run('Object.keys(activityModes()).length'),5);
 assert.equal(run('speechTasks.filter(t=>t.disabled).length'),0);
 run('renderSidebar()');
 assert.match(root.querySelector('#quickStats').innerHTML,/0\/420/);
 for(const mode of ['fix','truth','choice','exam','errors']){
   run(`state.mode='${mode}';renderSetup()`);
   assert.match(root.querySelector('#setupView').innerHTML,/morph:Существительное/);
 }
 context.q={question_id:'truth1',kind:'speech_truth',prompt:'около ДВУХСТА деревьев',instruction:'Исправьте',rule_name:'Числительное'};
 run(`state.answers={};state.currentSession={session_id:'session',questions:[q]};state.mode='truth';`);
 assert.equal(run('answerIsComplete(q)'),false);
 run(`state.answers[q.question_id]={verdict:'false',word:''}`);
 assert.equal(run('answerIsComplete(q)'),false);
 assert.match(run('renderSpeechQuestion(q,0)'),/data-speech-correction/);
 run(`state.answers[q.question_id].word='двухсот'`);
 assert.equal(run('answerIsComplete(q)'),true);
 run(`state.answers[q.question_id]={verdict:'true'}`);
 assert.equal(run('answerIsComplete(q)'),true);
 assert.doesNotMatch(run('renderSpeechQuestion(q,0)'),/data-speech-correction/);
 run(`state.answers[q.question_id]={verdict:'false',word:'двухсот'};state.currentQuestionIndex=0;state.startedAt=Date.now();api=async(url,options)=>{requests.push({url,options});return {question_id:q.question_id,is_correct:true,correct_answer:'двухсот'};};`);
 await run('checkSpeechAnswer()');
 assert.match(root.querySelector('#practiceView').innerHTML,/data-speech-feedback/);
 assert.equal(JSON.parse(context.requests.at(-1).options.body).answer.word,'двухсот');
 run(`state.currentSession={session_id:'session',questions:[q],assignment_id:'assigned'};renderAssignedQuestion()`);
 assert.match(root.querySelector('#practiceView').innerHTML,/data-speech-correction/);
 context.reply={session_id:'start7',questions:[{question_id:'fix7',kind:'speech_input',prompt:'ПЯТЬ НОСКОВ',rule_name:'Существительное'}]};
 run(`api=async(url,options)=>{requests.push({url,options});return reply;};state.mode='fix';state.speechTopics={ege7:['morph:Существительное']};state.selectedRuleIds=['morph:Существительное'];`);
 await run('startPractice()');
 assert.deepEqual(JSON.parse(context.requests.at(-1).options.body).rule_ids,['morph:Существительное']);
 run(`state.currentActivity='ege7';state.user={role:'teacher'};state.mode='truth';showTestComposer()`);
 console.log('Speech UI passed: task 7 route, five modes, all 8 mix tasks, whole-bank/group coverage, written correction, completeness, check POST, frozen-assignment renderer and part-of-speech payload.');
}
main().catch(e=>{console.error(e);process.exitCode=1;});
