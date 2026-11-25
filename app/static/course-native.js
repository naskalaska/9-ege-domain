/* Course controls added to the supplied documents, without a second page shell. */
(() => {
  'use strict';
  const cfg = window.__courseDocument;
  const { course, resource, lesson, token } = cfg;
  let progress = cfg.progress || {}, timer;
  const savedFields = cfg.fields;
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const isMap = resource === 'map', isExtra = resource.startsWith('extra-');
  document.body.classList.add('nv-document');
  document.body.dataset.courseResource=resource;
  const main = document.querySelector('main');
  const shell = main || document.body;
  const footer = document.querySelector('footer,.course-signature');
  const status = document.createElement('span');
  status.className = 'nv-status'; status.setAttribute('role','status'); status.setAttribute('aria-live','polite');

  async function action(body) {
    const response = await fetch('/api/courses/action', {method:'POST', headers:{'Content-Type':'application/json',Authorization:'Bearer '+token}, body:JSON.stringify(body)});
    const data = await response.json();
    if (!response.ok) throw Error(data.error || 'Не удалось сохранить изменения.');
    return data;
  }
  function notice(text) { status.textContent = text; }
  async function save() {
    if (isExtra) { progress.extras ||= {}; progress.extras[resource] = savedFields; }
    else if (!isMap) progress.fields = savedFields;
    await action({action:'progress',lesson_id:lesson?.id || 0,data:progress});
    notice('Сохранено');
  }
  function queueSave() {
    clearTimeout(timer); notice('Сохраняем…');
    timer = setTimeout(() => save().catch(error => notice(error.message)), 600);
  }
  function localLink(title, href, className='') {
    return `<a class="nv-link ${className}" href="${esc(href)}">${esc(title)}</a>`;
  }
  function externalLinks(items) {
    return (items || []).map(x => `<a class="nv-link" href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.title)} ↗</a>`).join('');
  }
  function appendBeforeFooter(element) {
    if (footer && shell.contains(footer)) footer.before(element);
    else shell.append(element);
  }
  function homeworkText(text) {
    return String(text || '').trim().split(/\n\s*\n/).map(block => {
      const lines=block.split('\n').map(line=>line.trim()).filter(Boolean);
      if(lines.every(line=>/^\d+[.)]\s/.test(line))) return '<ol>'+lines.map(line=>'<li>'+esc(line.replace(/^\d+[.)]\s+/,''))+'</li>').join('')+'</ol>';
      if(lines.every(line=>/^[-•]\s/.test(line))) return '<ul>'+lines.map(line=>'<li>'+esc(line.replace(/^[-•]\s+/,''))+'</li>').join('')+'</ul>';
      return '<p>'+lines.map(esc).join('<br>')+'</p>';
    }).join('');
  }

  // One slim row, integrated with the document's existing header.
  const tools = document.createElement('nav');
  tools.className='nv-tools'; tools.setAttribute('aria-label','Управление курсом');
  const chat = course.group?.chat || lesson?.chat || course.settings.chat;
  tools.innerHTML = (isMap ? localLink('← На сайт','/services') : localLink('← Карта курса','/courses/neurovisual','nv-map-back')) +
    (chat ? `<a class="nv-link nv-chat" href="${esc(chat)}" target="_blank" rel="noopener">Чат курса ↗</a>` : '');
  tools.append(status);
  if(course.preview) {
    const preview=document.createElement('a');preview.className='nv-preview';preview.textContent='Управление курсом';preview.href='/course-preview?mode=admin'+(lesson?'&lesson='+lesson.id:'');
    tools.append(preview);
  }
  if (isMap && document.querySelector('.top')) document.querySelector('.top').after(tools);
  else document.body.prepend(tools);

  if(resource==='extra-2'){
    const controls=document.querySelector('.controls');
    if(controls){
      const help=[];for(let node=controls.nextElementSibling;node&&node.matches('.note,.hint');node=node.nextElementSibling)help.push(node);
      const panel=document.createElement('details');panel.className='nv-prompt-settings';panel.open=savedFields['nv:settings-open']!==false;
      panel.innerHTML='<summary>Общие данные для промптов <span>развернуть / свернуть</span></summary><div class="nv-prompt-settings-body"></div>';
      controls.before(panel);panel.querySelector('div').append(controls);
      panel.querySelector('div').append(...help);
      const reset=document.createElement('button');reset.type='button';reset.className='btn secondary nv-reset-prompts';reset.textContent='Сбросить всё';
      controls.append(reset);
      reset.onclick=()=>{
        for(const id of ['topic','audience','style','reference','refMode','styleBoost','palette','search']){
          const field=document.getElementById(id);if(!field)continue;
          field.value=field.tagName==='SELECT'?'none':field.defaultValue;
          field.dispatchEvent(new Event('input',{bubbles:true}));
          if(field.tagName==='SELECT')field.dispatchEvent(new Event('change',{bubbles:true}));
        }
        notice('Все данные промптов сброшены');
      };
      panel.addEventListener('toggle',()=>{savedFields['nv:settings-open']=panel.open;queueSave();});
    }
    const count=document.getElementById('count');
    if(count){
      const plural=new Intl.PluralRules('ru');
      const update=()=>{const n=parseInt(count.textContent,10);if(!Number.isFinite(n))return;const text=n+' '+({one:'промпт',few:'промпта',many:'промптов',other:'промпта'}[plural.select(n)]);if(count.textContent!==text)count.textContent=text;};
      update();new MutationObserver(update).observe(count,{childList:true,characterData:true,subtree:true});
    }
  }

  if(resource==='extra-4'){
    const images=[...document.querySelectorAll('main img')].filter(img=>img.alt.trim()&&!img.closest('a,button')&&img.getAttribute('aria-hidden')!=='true');
    const dialog=document.createElement('dialog');dialog.className='nv-infographic-dialog nv-experiment-dialog';
    dialog.setAttribute('aria-label','Просмотр изображения');
    dialog.innerHTML='<div class="nv-infographic-toolbar"><span></span><button type="button" class="nv-infographic-zoom">Крупнее</button><button type="button" class="nv-infographic-close" aria-label="Закрыть изображение">× Закрыть</button></div><div class="nv-infographic-view"><img alt=""></div>';
    document.body.append(dialog);
    const preview=dialog.querySelector('img'),zoom=dialog.querySelector('.nv-infographic-zoom');
    function openImage(image){
      preview.src=image.currentSrc||image.src;preview.alt=image.alt;
      dialog.querySelector('.nv-infographic-toolbar>span').textContent=image.alt;
      dialog.style.setProperty('--nv-image-width',Math.max(image.naturalWidth||0,innerWidth*1.5)+'px');
      dialog.classList.remove('nv-zoomed');zoom.textContent='Крупнее';
      dialog.showModal();dialog.querySelector('.nv-infographic-view').scrollTo(0,0);
    }
    for(const image of images){
      image.classList.add('nv-enlargeable');image.tabIndex=0;image.setAttribute('role','button');
      image.setAttribute('aria-label','Увеличить: '+image.alt);image.setAttribute('aria-haspopup','dialog');image.title='Нажмите, чтобы увеличить';
      image.addEventListener('click',()=>openImage(image));
      image.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();openImage(image);}});
    }
    zoom.onclick=()=>{const enlarged=dialog.classList.toggle('nv-zoomed');zoom.textContent=enlarged?'Вписать в экран':'Крупнее';};
    dialog.querySelector('.nv-infographic-close').onclick=()=>dialog.close();
    dialog.addEventListener('click',event=>{if(event.target===dialog)dialog.close();});
  }

  if (isMap) {
    const completion=course.homework_progress||{completed:0,total:7};
    const progressBox=document.querySelector('.progress');
    if(progressBox){
      const meter=document.createElement('progress');meter.className='nv-homework-meter';meter.max=completion.total;meter.value=completion.completed;
      meter.setAttribute('aria-label','Выполненные домашние задания');
      meter.title='Выполнение домашних заданий отмечает преподаватель';
      progressBox.prepend(meter);
    }
    // Materials belong to the map. Each opens as its own full page.
    const board=document.querySelector('.board');
    const leaf=(title,short,href,index)=>{
      const positions=[[9,24,76,9],[27,10,19,28],[56,12,84,64],[69,78,15,68],[89,39,85,76]];
      const pos=positions[index%positions.length];
      return `<a class="nv-leaf" href="${esc(href)}" aria-label="${esc(title)}" title="${esc(title)}" style="--lx:${pos[0]}%;--ly:${pos[1]}%;--lmx:${pos[2]}%;--lmy:${pos[3]}%"><img src="/assets/course/painted-leaf.png" alt="" aria-hidden="true" draggable="false"><span>${esc(short)}</span><i aria-hidden="true">↗</i></a>`;
    };
    const materials=document.createElement('nav');materials.id='course-materials';materials.className='nv-leaves';materials.setAttribute('aria-label','Дополнительные материалы');
    const short=['Доступ к ChatGPT','Словарик','Промпты','Цветовой компас','Эксперименты'];
    materials.innerHTML=course.extras.map((x,index)=>leaf(x.title,short[index],'/courses/neurovisual?material='+x.id,index)).join('');
    if(board)board.append(materials);else appendBeforeFooter(materials);
    if(course.settings.links?.length){const bank=document.createElement('nav');bank.className='nv-leaf-bank';bank.setAttribute('aria-label','Материалы преподавателя');bank.innerHTML=course.settings.links.map((x,i)=>leaf(x.title,x.title,x.url,i+5)).join('');board?.after(bank);}
    const intro=document.querySelector('.hero-content .intro');
    // Keep the supplied title and composition; editable welcome text stays optional.
    if (intro && course.settings.intro && !course.settings.intro.startsWith('Добро пожаловать! Пройдите семь шагов')) intro.textContent=course.settings.intro;
    if(intro){const hint=document.createElement('span');hint.className='nv-leaf-hint';hint.textContent=' Листики — дополнительные материалы.';intro.append(hint);}
    const points=[...document.querySelectorAll('.flower-button')];
    points.forEach((point,index) => {
      const item=course.lessons[index];
      if(!item) return;
      if(!item.available) {
        point.classList.add('nv-locked');
        const label=point.querySelector('.status');
        if(label) label.textContent='Ещё не открыт';
      }
    });
    document.addEventListener('click', event => {
      const link=event.target.closest('#lesson-link');
      if(!link) return;
      const id=Number(new URL(link.href,location.href).searchParams.get('lesson'));
      const item=course.lessons.find(x=>x.id===id);
      if(item && !item.available) {
        event.preventDefault();
        const opens=item.effective_opens_at ?? item.opens_at;
        notice(opens && opens!=='manual' ? 'Урок откроется '+new Date(opens).toLocaleString('ru-RU',{timeZone:'Europe/Moscow'})+' МСК' : 'Преподаватель ещё не открыл этот урок.');
      }
    },true);
  }

  if (lesson && !isExtra) {
    const materials=document.createElement('details');materials.className='nv-lesson-materials';
    materials.innerHTML='<summary>Материалы занятия</summary><div>'+(lesson.links?.length?externalLinks(lesson.links):'<p>Материалы пока не добавлены.</p>')+'</div>';
    tools.querySelector('.nv-map-back').after(materials);
    const extras = document.createElement('div'); extras.className='nv-lesson-links';
    if(lesson.intro) { const text=document.createElement('p');text.textContent=lesson.intro;extras.prepend(text); }
    // Lesson 1 has two independent slots; other lessons keep one.
    const videoStack=document.createElement('div');videoStack.className='nv-video-stack';
    for(let videoIndex=0;videoIndex<(lesson.id===1?2:1);videoIndex++){
      const video=lesson.videos?.[videoIndex];
      const videoTitle=lesson.id===1?'Видео урока '+(videoIndex+1):'Видео урока';
      const section=document.createElement('section'); section.className='nv-video';section.setAttribute('aria-label',videoTitle);
      section.innerHTML='<div class="nv-video-heading">'+videoTitle+'</div>'+(video ?
        `<iframe src="${esc(video)}" title="${esc(videoTitle)}" allow="autoplay; fullscreen; encrypted-media; picture-in-picture" allowfullscreen></iframe>` :
        `<div class="nv-video-placeholder"><svg viewBox="0 0 64 64" aria-hidden="true"><circle cx="32" cy="32" r="28"/><path d="M27 20L46 32L27 44Z"/></svg><span>Видео занятия появится здесь</span>${course.preview?'<a href="/course-preview?mode=admin&lesson='+lesson.id+'">Добавить видео VK</a>':''}</div>`);
      if(video){
        const actions=document.createElement('div');actions.className='nv-video-actions';
        actions.innerHTML=`<a href="${esc(video)}" target="_blank" rel="noopener">Открыть видео отдельно ↗</a>`;
        if(course.preview&&location.hostname==='127.0.0.1'){
          const local=new URL(location.href);local.hostname='localhost';local.pathname='/course-preview';local.search='?lesson='+lesson.id;
          actions.insertAdjacentHTML('afterbegin',`<a href="${esc(local.href)}">Проверить плеер через localhost</a>`);
        }
        section.append(actions);
      }
      videoStack.append(section);
    }
    const header=document.querySelector('body > header');
    if(header) header.after(videoStack);else shell.prepend(videoStack);
    if(extras.childNodes.length) shell.prepend(extras);

    if(lesson.id===1){
      const slides=[
        ['infographic-bratuha-overview.png','Братуха.ру: возможности'],
        ['infographic-chatgpt.png','Прямой доступ к ChatGPT'],
        ['infographic-bratuha.png','Братуха.ру: плюсы и минусы'],
        ['infographic-chataibot.png','ChatAIbot: плюсы и минусы'],
        ['infographic-syntx.png','Syntx.ai: обзор возможностей'],
      ];
      const gallery=document.createElement('div');gallery.className='nv-infographics';gallery.setAttribute('role','region');gallery.setAttribute('aria-label','Инфографики об инструментах');
      gallery.innerHTML='<button type="button" class="nv-infographic-open" aria-label="Увеличить инфографику"><img alt="" decoding="async" loading="lazy"><span>Увеличить</span></button><div class="nv-carousel-controls"><button type="button" data-slide="-1">Предыдущая</button><span class="nv-carousel-caption" aria-live="polite"></span><button type="button" data-slide="1">Следующая</button></div>';
      const recommendation=document.getElementById('recommendation');
      if(recommendation)recommendation.after(gallery);else document.getElementById('access')?.append(gallery);
      const dialog=document.createElement('dialog');dialog.className='nv-infographic-dialog';
      dialog.innerHTML='<div class="nv-infographic-toolbar"><span></span><button type="button" class="nv-infographic-zoom">Крупнее</button><button type="button" class="nv-infographic-close">Закрыть</button></div><div class="nv-infographic-view"><img alt=""></div>';
      document.body.append(dialog);
      let slide=0;
      function showSlide(index){
        slide=(index+slides.length)%slides.length;const [file,title]=slides[slide];
        const src='/api/courses/asset?id='+encodeURIComponent(file);
        for(const img of [gallery.querySelector('img'),dialog.querySelector('img')]){img.src=src;img.alt=title;}
        gallery.querySelector('.nv-carousel-caption').textContent=(slide+1)+' / '+slides.length+' · '+title;
        dialog.querySelector('.nv-infographic-toolbar>span').textContent=title;
      }
      showSlide(0);
      gallery.querySelectorAll('[data-slide]').forEach(button=>button.onclick=()=>showSlide(slide+Number(button.dataset.slide)));
      gallery.addEventListener('keydown',event=>{if(['ArrowLeft','ArrowRight'].includes(event.key)){event.preventDefault();showSlide(slide+(event.key==='ArrowLeft'?-1:1));}});
      gallery.querySelector('.nv-infographic-open').onclick=()=>{dialog.classList.remove('nv-zoomed');dialog.querySelector('.nv-infographic-zoom').textContent='Крупнее';dialog.showModal();};
      dialog.querySelector('.nv-infographic-close').onclick=()=>dialog.close();
      dialog.querySelector('.nv-infographic-zoom').onclick=event=>{const zoomed=dialog.classList.toggle('nv-zoomed');event.target.textContent=zoomed?'Вписать в экран':'Крупнее';};
      dialog.addEventListener('click',event=>{if(event.target===dialog)dialog.close();});
    }

    // Reuse lesson 2's panel, keeping its interactive plan and export controls.
    let homework=lesson.id===2?document.querySelector('main #finish'):null;
    let panel=homework?.querySelector(':scope > .panel');
    if(homework && panel){
      homework.querySelector(':scope > .sectionhead')?.remove();
      panel.querySelector('.callout.homework')?.remove();
    } else {
      if(lesson.id===3) document.querySelector('#finish > .note')?.remove();
      if(lesson.id===6){
        const old=[...document.querySelectorAll('#finish > .note')].find(node=>node.querySelector('ol.steps'));
        if(old?.previousElementSibling?.tagName==='H3') old.previousElementSibling.remove();
        old?.remove();
      }
      if(lesson.id===7) document.querySelector('#final > .note.blue')?.remove();
      homework=document.createElement('section');homework.id='course-homework';
      panel=document.createElement('div');homework.append(panel);appendBeforeFooter(homework);
    }
    homework.classList.add('nv-homework-section');panel.classList.add('nv-homework-panel');
    const heading=document.createElement('div');heading.className='nv-homework-heading';
    heading.innerHTML='<h2>Домашнее задание</h2><p>Соберите результаты занятия и отправьте их одним сообщением в чат курса.</p>';
    homework.prepend(heading);
    const assignment=document.createElement('div');assignment.className='nv-homework-callout';assignment.dataset.nvAssignment='';
    assignment.innerHTML=`<h3 class="nv-homework-delivery">Что отправить ${chat?'<a href="'+esc(chat)+'" target="_blank" rel="noopener">в чат курса</a>':'в чат курса'}</h3><div class="nv-homework-text">${homeworkText(lesson.homework)}</div>`;
    panel.prepend(assignment);
    const finish=document.createElement('section');finish.className='nv-finish';finish.id='course-finish';
    finish.innerHTML=`<details class="nv-completion"><summary>Итоговый чек-лист</summary><div class="nv-completion-content"><h2>Итоговый чек-лист</h2>${lesson.checklist.map((text,i)=>`<label class="nv-check"><input type="checkbox" data-nv-check="${i}" ${progress.checks?.[i]?'checked':''}><span>${esc(text)}</span></label>`).join('')}</div></details><div class="nv-complete-row"><label class="nv-check"><input type="checkbox" id="nv-completed" ${progress.completed?'checked':''}><span>Урок пройден</span></label><button type="button" id="nv-save">Сохранить ответы</button></div>`;
    appendBeforeFooter(finish);
    const review=course.homework?.find(item=>item.lesson_id===lesson.id);
    const reviewStatus=document.createElement('p');reviewStatus.className='nv-homework-status';
    reviewStatus.textContent=review?.completed?'✓ Преподаватель отметил выполнение домашнего задания':'Выполнение домашнего задания отмечает преподаватель.';
    assignment.after(reviewStatus);
    finish.querySelectorAll('[data-nv-check]').forEach(el=>el.addEventListener('change',()=>{progress.checks||={};progress.checks[el.dataset.nvCheck]=el.checked;queueSave();}));
    finish.querySelector('#nv-completed').addEventListener('change',event=>{progress.completed=event.target.checked;queueSave();});
    finish.querySelector('#nv-save').onclick=()=>{clearTimeout(timer);save().catch(error=>notice(error.message));};
  }

  // Restore and capture the original interactive fields on the original page.
  const fields=[...document.querySelectorAll('input,textarea,select')].filter(el=>!el.closest('.nv-finish'));
  function fieldKey(el) { return el.id || el.name || el.dataset.save || 'field:'+fields.indexOf(el); }
  for(const el of fields) {
    const key=fieldKey(el);
    savedFields['label:'+key]=(el.labels?.[0]?.textContent||el.closest('label')?.textContent||el.placeholder||key).trim().slice(0,300);
    if(key in savedFields) {
      if(['checkbox','radio'].includes(el.type)) el.checked=!!savedFields[key]; else el.value=savedFields[key];
    }
  }
  if(resource==='extra-2'){
    document.getElementById('topic')?.dispatchEvent(new Event('input',{bubbles:true}));
    document.getElementById('search')?.dispatchEvent(new Event('input',{bubbles:true}));
  }
  document.addEventListener('input',event=>{
    const el=event.target;
    if(!el.matches('input,textarea,select') || el.closest('[data-nv-ui],.nv-finish')) return;
    if(!fields.includes(el)) fields.push(el);
    savedFields[fieldKey(el)]=['checkbox','radio'].includes(el.type)?el.checked:el.value;
    queueSave();
  });
  window.addEventListener('course-storage',event=>{
    savedFields['storage:'+event.detail.key]=event.detail.value;
    if(!isMap)queueSave();
  });

  if(!isExtra) {
    const messages=document.createElement('details');messages.className='nv-correspondence';messages.dataset.nvUi='';
    const ownMessages=course.messages.filter(m=>m.lesson_id===(lesson?.id||0));
    messages.innerHTML=`<summary>Вопрос преподавателю · обратная связь${ownMessages.length?' ('+ownMessages.length+')':''}</summary><form id="nv-message"><label>Тип сообщения<select name="kind"><option value="question">Вопрос</option><option value="feedback">Обратная связь</option></select></label><label>Сообщение<textarea name="body" required maxlength="20000"></textarea></label><button type="submit">Отправить</button><span class="nv-message-status" role="status"></span></form><div class="nv-message-list">${ownMessages.map(m=>`<article><p>${esc(m.body)}</p>${m.reply?'<p class="nv-reply"><b>Ответ преподавателя:</b> '+esc(m.reply)+'</p>':'<small>Ожидает ответа</small>'}</article>`).join('')}</div>`;
    appendBeforeFooter(messages);
    messages.querySelector('form').onsubmit=async event=>{
      event.preventDefault();const form=event.currentTarget,button=form.querySelector('button'),result=form.querySelector('.nv-message-status');
      button.disabled=true;
      try {
        const data=Object.fromEntries(new FormData(form));
        await action({action:'message',lesson_id:lesson?.id||0,...data});
        const item=document.createElement('article');const body=document.createElement('p');body.textContent=data.body;item.append(body);
        const waiting=document.createElement('small');waiting.textContent='Ожидает ответа';item.append(waiting);
        messages.querySelector('.nv-message-list').append(item);form.reset();result.textContent='Отправлено';
      } catch(error) { result.textContent=error.message; }
      finally { button.disabled=false; }
    };
  }

  // Course navigation replaces the document in this tab, keeping the preview toolbar.
  if(lesson&&chat){
    const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
    const nodes=[];while(walker.nextNode())nodes.push(walker.currentNode);
    for(const node of nodes){
      if(node.parentElement.closest('script,style,textarea,code,pre,a,.nv-tools,.nv-finish,.nv-correspondence,.nv-video'))continue;
      const pattern=/чат(?:а|е|у)?\s+(?:обучения|курса)/gi;
      if(!pattern.test(node.textContent))continue;
      const fragment=document.createDocumentFragment();let start=0;
      for(const match of node.textContent.matchAll(/чат(?:а|е|у)?\s+(?:обучения|курса)/gi)){
        fragment.append(document.createTextNode(node.textContent.slice(start,match.index)));
        const link=document.createElement('a');link.href=chat;link.target='_blank';link.rel='noopener';link.className='nv-source-chat';link.textContent=match[0].replace('обучения','курса');fragment.append(link);start=match.index+match[0].length;
      }
      fragment.append(document.createTextNode(node.textContent.slice(start)));node.replaceWith(fragment);
    }
  }
  document.addEventListener('click',event=>{
    const link=event.target.closest('a');if(!link || event.defaultPrevented) return;
    const url=new URL(link.getAttribute('href'),location.href);
    if(url.pathname==='/courses/neurovisual') {event.preventDefault();location.href=url.href;}
    else if(url.pathname==='/api/courses/content') {
      const match=(url.searchParams.get('resource')||'').match(/^extra-(\d+)$/);
      if(match){event.preventDefault();location.href='/courses/neurovisual?material='+match[1];}
    }
  });
})();
