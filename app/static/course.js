(() => {
'use strict';
const root=document.querySelector('#course'), statusEl=document.querySelector('#course-status');
const admin=location.pathname==='/admin/courses';
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let course,activeLesson=Number(new URLSearchParams(location.search).get('lesson')||0);
async function request(url,body){const r=await fetch(url,{headers:{Authorization:'Bearer '+(localStorage.getItem('ege_token')||''),...(body?{'Content-Type':'application/json'}:{})},...(body?{method:'POST',body:JSON.stringify(body)}:{})});const data=await r.json();if(!r.ok)throw Error(data.error||'Не удалось выполнить действие.');return data;}
const action=body=>request('/api/courses/action',body);
function notify(text,error=false){statusEl.textContent=text;statusEl.style.color=error?'#962e41':'#14365f';}
function label(title,name,value,type='text'){return `<label>${title}${type==='textarea'?`<textarea name="${name}">${esc(value)}</textarea>`:`<input type="${type}" name="${name}" value="${esc(value)}">`}</label>`;}
const linksText=items=>(items||[]).map(x=>x.title+' | '+x.url).join('\n');
function parseLinks(value){return value.split('\n').filter(x=>x.trim()).map(line=>{const index=line.indexOf('|');if(index<0)throw Error('Запишите ссылки в формате: Название | https://…');return {title:line.slice(0,index).trim(),url:line.slice(index+1).trim()};});}
function opening(l){const v=l.effective_opens_at??l.opens_at;return v==='manual'?'Ожидает открытия':v?'Открытие: '+new Date(v).toLocaleString('ru-RU',{timeZone:'Europe/Moscow'})+' МСК':'Доступ открыт';}
async function renderLearner() {
  const lesson=course.lessons.find(x=>x.id===activeLesson);
  if(activeLesson&&!lesson)throw Error('Урок не найден.');
  if(lesson&&!lesson.available){
    root.innerHTML=`<p>${esc(opening(lesson))}</p><a href="/courses/neurovisual">← Карта курса</a>`;
    return;
  }
  const material=new URLSearchParams(location.search).get('material');
  const resource=material!==null?'extra-'+Number(material):(lesson?String(lesson.id):'map');
  const progress=structuredClone(course.progress.find(p=>p.lesson_id===(lesson?.id||0))?.data||{});
  const response=await fetch('/api/courses/content?resource='+encodeURIComponent(resource),{headers:{Authorization:'Bearer '+(localStorage.getItem('ege_token')||'')}});
  if(!response.ok){const data=await response.json();throw Error(data.error);}
  let source=await response.text();
  const configuration=JSON.stringify({course,lesson,progress,resource,token:localStorage.getItem('ege_token')||''}).replace(/</g,'\u003c');
  const setup=`<script>(function(){const cfg=${configuration};window.__courseDocument=cfg;window.__courseRealStorage=window.localStorage;cfg.fields=cfg.resource.startsWith('extra-')?((cfg.progress.extras||={})[cfg.resource]||={}):(cfg.progress.fields||={});const values=cfg.fields;const storage={getItem:k=>values['storage:'+k]??null,setItem:(k,v)=>{values['storage:'+k]=String(v);window.dispatchEvent(new CustomEvent('course-storage',{detail:{key:k,value:String(v)}}))},removeItem:k=>{delete values['storage:'+k]},clear:()=>Object.keys(values).filter(k=>k.startsWith('storage:')).forEach(k=>delete values[k]),key:i=>Object.keys(values).filter(k=>k.startsWith('storage:'))[i]?.slice(8)??null};try{Object.defineProperty(window,'localStorage',{value:storage})}catch(e){}})();<\/script>`;
  source=source.replace(/<head[^>]*>/i,match=>match+setup);
  source=source.replace(/<\/head>/i,'<link rel="stylesheet" href="/course-native.css?v=20261125-course-v12"><script src="/course-native.js?v=20261125-course-v12" defer><\/script></head>');
  document.open();document.write(source);document.close();
}
async function renderAdmin(){const module=await import('/course-admin.js?v=20261125-course-v12');await module.renderCourseAdmin({root,course,request,action,notify,reload:load});}
async function load(){try{course=await request('/api/courses'+(admin?'/admin':''));if(['127.0.0.1','localhost'].includes(location.hostname)&&localStorage.getItem('course_preview')==='1')course.preview=true;await (admin?renderAdmin():renderLearner());}catch(e){root.innerHTML=`<section class="course-hero"><h1>${admin?'Управление курсами':'Нейровизуал в работе учителя'}</h1><p>${esc(e.message)}</p><p>Для доступа к покупке войдите или зарегистрируйтесь с той почтой, которую указали при оплате. После входа вернитесь по ссылке «Мой курс».</p><div class="course-actions"><a class="primary-button" href="/login?next=${encodeURIComponent(location.pathname+location.search)}">Войти</a><a class="secondary-button" href="/register?role=teacher&next=/courses/neurovisual">Зарегистрироваться</a><a class="secondary-button" href="/shop/neurovisual">Купить курс</a></div></section>`;}}
load();
})();
