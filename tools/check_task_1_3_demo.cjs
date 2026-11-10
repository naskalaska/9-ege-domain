// Exercise session creation, multi-select grading, error repetition and text formatting.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const bank=JSON.parse(fs.readFileSync('task_1_3_trainer_bank.json','utf8'));
const nodes=new Map();let checked=[];
function node(id){if(!nodes.has(id))nodes.set(id,{value:'',innerHTML:'',textContent:'',style:{},firstChild:{textContent:''},classList:{toggle(){},add(){}},setAttribute(){},querySelectorAll(){return[];},insertAdjacentHTML(_,html){this.innerHTML+=html;},focus(){}});return nodes.get(id);}
const document={querySelector:node,querySelectorAll:s=>s==='[name="answer"]:checked'?checked.map(n=>({value:String(n)})):[]};
const context=vm.createContext({document,BANK:bank,localStorage:{getItem(){return null;},setItem(){}},console,confirm:()=>true});
node('#mode').value='gap';node('#topic').value='all';node('#amount').value='all';
vm.runInContext(fs.readFileSync('app/static/task-1-3/trainer.js','utf8'),context);
const evaluate=s=>vm.runInContext(s,context);
// The screenshot's text must flow naturally without deleting paragraph boundaries.
const source=bank[47];evaluate(`context({source:BANK[47],n:3})`);
assert(!node('#contextText').innerHTML.includes('\n'));
assert(node('#contextText').innerHTML.includes('в своих чистых и строгих очертаниях'));
assert.equal((node('#contextText').innerHTML.match(/<p>/g)||[]).length,source.text.trim().split(/\n[ \t]*\n+/).length);
// Formatting after marking must not shift any lexical highlight.
for(const s of bank)for(const opt of s.tasks[2].options){if(!opt.range)continue;context.q={source:s,n:2,opt};evaluate('context(q)');assert(node('#contextText').innerHTML.includes('<mark>'+s.text.slice(...opt.range)+'</mark>'));}
node('#mode').value='characteristics';node('#topic').value='all';evaluate('topics();start()');
assert.equal(evaluate('run.length'),86);assert(evaluate('run.every(q=>q.kind==="full"&&q.n===3)'));
assert.equal((node('#card').innerHTML.match(/type="checkbox"/g)||[]).length,5);
assert(!node('#card').innerHTML.includes('Правильный ответ:'));
// An incomplete selection is wrong; the complete set is accepted independent of order.
const right=evaluate('run[0].source.tasks[3].options.filter(o=>o.right).map(o=>o.n)');
checked=Array.from(right).slice(1);if(!checked.length)checked=[6];node('#check').onclick();
assert.equal(evaluate('session[0].ok'),false);assert(evaluate('unresolved().has(run[0].id)'));
evaluate('render()');checked=Array.from(right).reverse();node('#check').onclick();
assert.equal(evaluate('session[1].ok'),true);assert(!evaluate('unresolved().has(run[0].id)'));
// Filters must apply to both task 3 modes.
for(const mode of ['truth','characteristics']){node('#mode').value=mode;evaluate('topics()');node('#topic').value='Официально-деловой';evaluate('start()');assert(evaluate('run.length>0 && run.every(q=>q.source.style==="Официально-деловой")'));}
// Existing lexical, gap and exam pools still work.
for(const [mode,count]of [['gap',86],['lex',429],['exam',85]]){node('#mode').value=mode;node('#topic').value='all';evaluate('start()');assert.equal(evaluate('run.length'),count);}
new vm.Script(fs.readFileSync('Тренажёр_ЕГЭ_1-3_демо.html','utf8').match(/<script>([\s\S]*)<\/script>/)[1]);
console.log('Passed: flowing paragraphs, all 429 highlights, 86 full task-3 questions, style filters, complete-set grading, resolved errors, existing session modes, standalone script syntax.');
