// Rebuild the portable demo from the original v32 database; never edits its keys.
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const db = JSON.parse(fs.readFileSync(path.join(root, 'task_1_3_content_fixed_v32.json'), 'utf8'));
// Editorial classification of the whole text, not of every style mentioned in an option.
// N = scientific (including popular science), P = publicistic, H = literary,
// D = official/business, R = conversational (personal letters).
const styles = `H P P H P N N P H N N D P H P H N D N N N P N N N H N D D R P H N D R N
P N N P D N P N H P D P P H N N P P N P P P D R N N D P D D N N N N P N N H H H H P P P H H P P P H`.split(/\s+/);
const labels = {N:'Научный', P:'Публицистический', H:'Художественный', D:'Официально-деловой', R:'Разговорный'};
const norm = s => s.toLowerCase().replace(/ё/g,'е');
const corrections = {'13:3':'пору','16:5':'содержит','29:3':'всё','35:4':'пересечённых','48:4':'ищет','49:2':'пеклась','56:2':'читал','71:4':'отцом','72:2':'берущем','77:2':'поднялся'};
function locate(text, lemma, key) {
  const words = [...text.matchAll(/[А-Яа-яЁё]+(?:-[А-Яа-яЁё]+)*/g)];
  if(corrections[key]) {
    const exact=words.find(w=>w[0].toLowerCase()===corrections[key]);
    if(!exact)throw new Error(`Missing explicit highlight ${key}`);
    return {start:exact.index,end:exact.index+exact[0].length,word:exact[0],score:100};
  }
  const l = norm(corrections[key] || lemma);
  const scored = words.map(w => {
    const v=norm(w[0]); let common=0;while(common<Math.min(v.length,l.length)&&v[common]===l[common])common++;
    return {start:w.index,end:w.index+w[0].length,word:w[0],score:v===l?100:common>=Math.min(3,l.length)?common*5-Math.abs(v.length-l.length):0};
  }).sort((a,b)=>b.score-a.score);
  return scored[0]?.score>0 ? scored[0] : null;
}
const audit=[];
const bank=db.entries.map((e,i)=>{
  const tasks = Object.fromEntries(e.tasks.map(t=>[t.number,{
    id:t.task_id,
    prompt:t.clean_text.replace(/^\d+\.\s*/, '').split(/\n\s*1\)/)[0].replace(/\n*Ответ:[\s\S]*$/, '').trim(),
    valid:t.valid_answers, answer:t.answer,
    why:t.methodical?.explanation?.text || '',
    options:(t.structured?.options||[]).map((o,oi)=>{
      const number=o.number??o.index??oi+1;
      const lemma=o.lemma_candidate || o.text.match(/^[А-ЯЁ][А-ЯЁа-яё-]+/)?.[0];
      const hit=t.number===2?locate(e.shared_context.text,lemma,`${i}:${number}`):null;
      if(t.number===2) audit.push({i,n:number,lemma,hit:hit?.word,score:hit?.score});
      return {n:number,text:o.text.replace(/\s*Ответ:\s*_+[.]?\s*$/, ''),right:o.correct_according_to_published_key,why:o.explanation?.text||o.explanation?.draft||'',lemma,range:hit?[hit.start,hit.end]:null};
    })
  }]));
  const req=e.tasks[0].methodical?.grammatical_requirement||'';
  const topic=/местоимени|союзное слово/.test(req)?'Местоимения и союзные слова':/наречи/.test(req)?'Наречия':/предлог/.test(req)?'Предлоги':/частиц/.test(req)?'Частицы':/союз/.test(req)?'Союзы':/числительн/.test(req)?'Числительные':'Вводные слова и конструкции';
  return {id:e.card_id,text:e.shared_context.text,topic,style:labels[styles[i]],tasks};
});
if(bank.length!==86 || styles.length!==86)throw new Error(`Count mismatch: bank ${bank.length}, styles ${styles.length}`);
fs.writeFileSync(path.join(root,'task_1_3_trainer_bank.json'),JSON.stringify(bank));
fs.writeFileSync(path.join(root,'tools/task_1_3_highlight_audit.json'),JSON.stringify(audit,null,2));
const background='data:image/png;base64,'+fs.readFileSync(path.join(root,'app/static/assets/redesign/tile-trainer.png')).toString('base64');
const css=fs.readFileSync(path.join(root,'app/static/task-1-3/trainer.css'),'utf8').replace('/* TRAINER_BACKGROUND */',background);
const js=fs.readFileSync(path.join(root,'app/static/task-1-3/trainer.js'),'utf8');
const template=fs.readFileSync(path.join(root,'app/static/task-1-3/template.html'),'utf8');
const html=template.replace('/* STYLES */',css).replace('/* BANK */',`const BANK = ${JSON.stringify(bank).replace(/</g,'\\u003c')};`).replace('/* TRAINER */',js);
fs.writeFileSync(path.join(root,'Тренажёр_ЕГЭ_1-3_демо.html'),html);
console.log(`Built ${bank.length} texts, ${bank.length*3} tasks; lexical highlights: ${audit.filter(x=>x.hit).length}/430.`);
