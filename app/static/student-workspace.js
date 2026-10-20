/* Pupil cards and calendar share the same assignments and permissions. */
function deadlineHtml(item) {
  if (!item.due_at) return '<span class="muted">Без срока</span>';
  return `<span class="${item.overdue ? 'deadline-overdue' : 'muted'}">${item.overdue ? 'Просрочено · ' : ''}Срок: <time datetime="${escapeHtml(item.due_at)}">${new Date(item.due_at).toLocaleString('ru-RU')}</time>${item.submitted_late ? ' · Сдано после срока' : ''}</span>`;
}

function deadlineFields(value = '') {
  const date = value ? new Date(value) : null;
  const local = date ? new Date(date.getTime()-date.getTimezoneOffset()*60000).toISOString().slice(0,16) : '';
  return `<label>Срок выполнения (ваше местное время)<input type="datetime-local" data-due-at value="${local}"></label><p class="muted">Можно оставить без срока. После просрочки работа остаётся доступной для выполнения.</p>`;
}

function dueFrom(root) {
  const value = root.querySelector('[data-due-at]')?.value;
  return value ? new Date(value).toISOString() : null;
}

async function editAssignmentDeadline(testId,studentId='',value='',refresh=showAssignments) {
  const modal = learningModal('Срок выполнения');
  const root = modal.querySelector('[data-content]');
  root.innerHTML = `${deadlineFields(value)}<p class="error" role="alert"></p><button class="primary-button" data-save-deadline>Сохранить срок</button>`;
  root.querySelector('button').onclick = async event => {
    event.target.disabled = true;
    try {
      await api('/api/assignments/deadline',{method:'POST',body:JSON.stringify({test_id:testId,student_id:studentId,due_at:dueFrom(root)})});
      modal.remove();await refresh();
    } catch (err) { root.querySelector('.error').textContent=err.message;event.target.disabled=false; }
  };
}

async function repeatFromError(attemptId,questionId='') {
  const teacher = state.user.role === 'teacher';
  const modal = learningModal(teacher ? 'Назначить повторение ошибки' : 'Повторение ошибки');
  const root = modal.querySelector('[data-content]');
  root.innerHTML = `<p>${teacher ? 'Будет назначена короткая работа ученику, который допустил эту ошибку.' : 'Вы решите задание ещё раз. Новая попытка сохранится в вашей статистике.'}</p>${teacher ? deadlineFields() : ''}<p class="error" role="alert"></p><button class="primary-button" data-repeat-confirm>${teacher ? 'Назначить повторение' : 'Начать повторение'}</button>`;
  root.querySelector('[data-repeat-confirm]').onclick = async event => {
    event.target.disabled = true;
    try {
      const result = await api('/api/errors/repeat',{method:'POST',body:JSON.stringify({attempt_id:attemptId,question_id:questionId,...(teacher ? {due_at:dueFrom(root)} : {})})});
      if (teacher) root.innerHTML = `<p role="status">${result.existing ? 'У ученика уже есть незавершённое повторение этой ошибки.' : 'Повторение назначено ученику.'}</p>`;
      else { await leaveAssignedWorkspace();document.querySelectorAll('.modal-backdrop').forEach(el=>el.remove());await openAssignedTest(result.id); }
      refreshAssignmentButton();
    } catch (err) { root.querySelector('.error').textContent=err.message;event.target.disabled=false; }
  };
}

document.addEventListener('click',event => {
  const repeat = event.target.closest('[data-repeat-error]');
  if (repeat) repeatFromError(repeat.dataset.repeatError);
  const question = event.target.closest('[data-repeat-question]');
  if (question) repeatFromError('',question.dataset.repeatQuestion);
  const profile = event.target.closest('[data-open-student-card]');
  if (profile) showStudentProfile(profile.dataset.openStudentCard);
});

function workspaceAssignmentCard(test) {
  const teacher = state.user.role === 'teacher';
  const status = test.revoked_at ? 'Отозван' : test.completed_at ? 'Завершён' : test.overdue ? 'Просрочен · можно выполнить' : test.started_at ? 'Начат' : 'Назначен';
  return `<article class="question workspace-assignment"><h3>${escapeHtml(test.title)}</h3>${teacher && test.display_name ? `<p>${escapeHtml(test.display_name)}</p>` : ''}<p>${escapeHtml(assignmentOutline(test))}</p><p>${deadlineHtml(test)}</p><p>${status} · проверено ${test.checked} из ${test.total}</p><div class="practice-actions">${teacher ? `<button class="secondary-button" data-work-results="${escapeHtml(test.id)}" data-student="${escapeHtml(test.student_id)}">Ответы ученика</button><button class="ghost-button" data-work-deadline="${escapeHtml(test.id)}" data-student="${escapeHtml(test.student_id)}" data-due="${escapeHtml(test.due_at || '')}">Изменить срок</button>` : !test.revoked_at || test.completed_at ? `<button class="primary-button" data-work-open="${escapeHtml(test.id)}">${test.completed_at ? 'Результаты' : test.started_at ? 'Продолжить' : 'Открыть'}</button>` : ''}</div></article>`;
}

function bindWorkspaceAssignments(root,refresh) {
  root.querySelectorAll('[data-work-results]').forEach(b=>b.onclick=()=>showAssignedResults(b.dataset.workResults,b.dataset.student));
  root.querySelectorAll('[data-work-deadline]').forEach(b=>b.onclick=()=>editAssignmentDeadline(b.dataset.workDeadline,b.dataset.student,b.dataset.due,refresh));
  root.querySelectorAll('[data-work-open]').forEach(b=>b.onclick=async()=>{
    b.disabled=true;
    try { await openAssignedTest(b.dataset.workOpen); } catch(err) { b.disabled=false;alert(err.message); }
  });
}

async function startStudentPage(path,updateUrl) {
  await leaveAssignedWorkspace();
  statisticsRequest++;++state.activityLoadRequestId;stopTeacherStatsRefresh();
  state.currentSession=null;state.currentActivity=null;
  document.querySelectorAll('.modal-backdrop').forEach(el=>el.remove());
  if (updateUrl) history.pushState(null,'',path);
  renderTopActions();window.scrollTo(0,0);
  view.innerHTML='<section class="statistics-page student-workspace" role="status">Загрузка…</section>';
  return view.firstElementChild;
}

async function showStudentProfile(studentId='',updateUrl=true) {
  let root;
  try {
    root = await startStudentPage(studentId ? '/apps/student/'+encodeURIComponent(studentId) : '/apps/profile',updateUrl);
    const params={student_id:studentId,offset_minutes:-new Date().getTimezoneOffset()};
    const data=await api('/api/students/profile?'+new URLSearchParams(params));
    if (!root.isConnected) return;
    root.removeAttribute('role');
    const teacher=state.user.role==='teacher';
    root.innerHTML=`<div class="panel-head"><div><p class="eyebrow">Единая карточка ученика</p><h2>${escapeHtml(data.student.display_name)}</h2></div><button class="secondary-button" data-card-calendar>Календарь</button></div><p>Группы: ${data.groups.map(g=>escapeHtml(g.title)).join(', ') || 'не назначены'}</p>${statisticsMetrics(data.statistics.summary)}<p>К выполнению: <b>${data.pending}</b> · просрочено: <b>${data.overdue}</b></p><nav class="student-card-sections" aria-label="Разделы карточки"><a href="#card-assignments">Работы</a><a href="#card-progress">Прогресс</a><a href="#card-errors">Ошибки и повторение</a></nav><h3 id="card-assignments">Назначенные работы</h3><label>Показать<select data-card-status><option value="pending">К выполнению</option><option value="all">Все работы</option><option value="overdue">Просроченные</option><option value="completed">Завершённые</option></select></label><div data-card-tests></div><h3 id="card-progress">Прогресс по заданиям и играм</h3>${statisticsActivityTable(data.statistics)}<h3>Динамика за 8 недель</h3><div class="statistics-table-wrap"><table class="table"><tr><th>Неделя с</th><th>Решено</th><th>Точность</th><th>Верные ответы</th></tr>${data.trend.map(w=>`<tr><td>${new Date(w.week+'T12:00:00').toLocaleDateString('ru-RU')}</td><td>${w.total}</td><td>${w.total ? w.accuracy+'%' : '—'}</td><td><meter min="0" max="100" value="${w.accuracy || 0}" aria-label="Точность за неделю"></meter> ${w.correct}</td></tr>`).join('')}</table></div>${statisticsTopics(data.statistics)}<h3 id="card-errors">Ошибки и повторение</h3><p class="muted">${teacher ? 'Назначьте повторение прямо из ошибочного решения.' : 'Нажмите «Повторить ошибку», чтобы решить задание ещё раз.'} Старая ошибка останется в истории.</p><div data-card-history></div>`;
    const renderTests=()=>{
      const status=root.querySelector('[data-card-status]').value;
      const tests=data.assignments.filter(t=>status==='all' || (status==='completed' ? t.completed_at : status==='overdue' ? t.overdue : !t.completed_at&&!t.revoked_at));
      const target=root.querySelector('[data-card-tests]');target.innerHTML=tests.map(workspaceAssignmentCard).join('') || '<p class="muted">Работ в этом списке нет.</p>';
      bindWorkspaceAssignments(target,()=>showStudentProfile(studentId,false));
    };
    root.querySelector('[data-card-status]').onchange=renderTests;renderTests();
    root.querySelector('[data-card-calendar]').onclick=()=>showAssignmentCalendar(studentId);
    mountStatisticsHistory(root.querySelector('[data-card-history]'),data.statistics,{student_id:data.student.user_id});
  } catch(err) { if (root?.isConnected) root.textContent=err.message;else alert(err.message); }
}

async function showAssignmentCalendar(studentId='',updateUrl=true) {
  let root;
  try {
    root=await startStudentPage('/apps/calendar'+(studentId?'?student_id='+encodeURIComponent(studentId):''),updateUrl);
    const data=await api('/api/assignments/calendar?'+new URLSearchParams({student_id:studentId}));
    if (!root.isConnected) return;
    root.removeAttribute('role');
    const now=new Date();let month=new Date(now.getFullYear(),now.getMonth(),1),selectedDay='';
    const dayKey=d=>`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
    root.innerHTML=`<div class="panel-head"><h2>Календарь работ</h2><button class="secondary-button" data-calendar-today>Текущий месяц</button></div><p class="muted">Просроченные работы остаются доступными для выполнения. Сроки показаны в вашем местном времени.</p>${data.role==='teacher'&&!studentId ? `<label>Ученик<select data-calendar-student><option value="">Все ученики</option>${data.students.map(p=>`<option value="${escapeHtml(p.user_id)}">${escapeHtml(p.display_name)}</option>`).join('')}</select></label>`:''}<div class="panel-head"><button class="ghost-button" data-month-prev aria-label="Предыдущий месяц">←</button><h3 data-month-title></h3><button class="ghost-button" data-month-next aria-label="Следующий месяц">→</button></div><div class="assignment-calendar" data-calendar-grid></div><div data-calendar-work></div><h3>Просроченные работы за все месяцы</h3><div data-calendar-overdue></div><details><summary>Работы без срока</summary><div data-calendar-undated></div></details>`;
    const draw=()=>{
      const pupil=root.querySelector('[data-calendar-student]')?.value;
      const all=data.items.filter(t=>!pupil||t.student_id===pupil);
      root.querySelector('[data-month-title]').textContent=month.toLocaleDateString('ru-RU',{month:'long',year:'numeric'});
      const first=(month.getDay()+6)%7,last=new Date(month.getFullYear(),month.getMonth()+1,0).getDate();
      let cells=['Пн','Вт','Ср','Чт','Пт','Сб','Вс'].map(d=>`<b>${d}</b>`).join('')+'<span></span>'.repeat(first);
      for(let i=1;i<=last;i++){
        const key=dayKey(new Date(month.getFullYear(),month.getMonth(),i));
        const tests=all.filter(t=>t.due_at&&dayKey(new Date(t.due_at))===key&&!t.revoked_at);
        cells+=`<button type="button" data-calendar-day="${key}" class="calendar-day ${key===dayKey(now)?'calendar-today':''} ${key===selectedDay?'selected':''}" aria-label="${key}, работ: ${tests.length}" ${key===selectedDay?'aria-pressed="true"':'aria-pressed="false"'}><b>${i}</b>${tests.length?`<small>${tests.length} раб.</small>`:''}${tests.some(t=>t.overdue)?'<span class="deadline-overdue">!</span>':''}</button>`;
      }
      root.querySelector('[data-calendar-grid]').innerHTML=cells;
      const monthTests=all.filter(t=>t.due_at&&!t.revoked_at&&(selectedDay?dayKey(new Date(t.due_at))===selectedDay:new Date(t.due_at).getFullYear()===month.getFullYear()&&new Date(t.due_at).getMonth()===month.getMonth())).sort((a,b)=>a.due_at.localeCompare(b.due_at));
      const target=root.querySelector('[data-calendar-work]');
      target.innerHTML=`<h3>${selectedDay?'Работы на '+new Date(selectedDay+'T12:00:00').toLocaleDateString('ru-RU'):'Работы месяца'}</h3>${selectedDay?'<button class="ghost-button" data-all-month>Весь месяц</button>':''}`+(monthTests.map(workspaceAssignmentCard).join('')||'<p>Работ нет.</p>');
      root.querySelector('[data-all-month]')?.addEventListener('click',()=>{selectedDay='';draw();});
      root.querySelector('[data-calendar-overdue]').innerHTML=all.filter(t=>t.overdue).map(workspaceAssignmentCard).join('')||'<p>Просроченных работ нет.</p>';
      root.querySelector('[data-calendar-undated]').innerHTML=all.filter(t=>!t.due_at&&!t.revoked_at).map(workspaceAssignmentCard).join('')||'<p>Работ без срока нет.</p>';
      root.querySelectorAll('[data-calendar-day]').forEach(b=>b.onclick=()=>{selectedDay=b.dataset.calendarDay;draw();});
      bindWorkspaceAssignments(root,()=>showAssignmentCalendar(studentId,false));
    };
    root.querySelector('[data-month-prev]').onclick=()=>{month=new Date(month.getFullYear(),month.getMonth()-1,1);selectedDay='';draw();};
    root.querySelector('[data-month-next]').onclick=()=>{month=new Date(month.getFullYear(),month.getMonth()+1,1);selectedDay='';draw();};
    root.querySelector('[data-calendar-today]').onclick=()=>{month=new Date(now.getFullYear(),now.getMonth(),1);selectedDay='';draw();};
    root.querySelector('[data-calendar-student]')?.addEventListener('change',()=>{selectedDay='';draw();});draw();
  } catch(err) { if(root?.isConnected)root.textContent=err.message;else alert(err.message); }
}
