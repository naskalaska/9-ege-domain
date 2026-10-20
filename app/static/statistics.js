/* Shared navigation and cross-activity statistics. */
let statisticsRequest = 0;
let platformNavigationObserver;

async function leaveAssignedWorkspace() {
  if (state.currentSession?.assignment_id && !state.currentSession.result) await persistAssignedAnswers();
  clearTimeout(assignmentSaveTimer);
}

function renderPlatformNavigation() {
  platformNavigationObserver?.disconnect();
  document.querySelector('#workspaceNavigation')?.remove();
  if (!state.user || !['teacher','student'].includes(state.user.role)) return;
  const nav = document.createElement('nav');
  nav.id = 'workspaceNavigation';nav.className = 'workspace-navigation';nav.setAttribute('aria-label','Быстрый переход между тренажёрами');
  nav.innerHTML = Object.entries(activityMeta).map(([slug,meta]) => `<a href="${slug === 'html-games' ? '/apps/mini' : '/apps/'+slug}" data-platform-activity="${slug}" ${state.currentActivity === slug && location.pathname !== '/apps/statistics' ? 'aria-current="page"' : ''}>${escapeHtml(meta.shortTitle || meta.title)}</a>`).join('');
  document.querySelector('.topbar').after(nav);
  const header = document.querySelector('.topbar');
  const setOffset = () => document.documentElement.style.setProperty('--workspace-header-height',header.offsetHeight+'px');
  platformNavigationObserver = new ResizeObserver(setOffset);
  platformNavigationObserver.observe(header);setOffset();
  nav.querySelectorAll('a').forEach(link => link.onclick = async event => {
    if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    try {
      await leaveAssignedWorkspace();
      statisticsRequest++;
      stopTeacherStatsRefresh();
      document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
      await loadActivity(link.dataset.platformActivity);
    } catch (err) { alert(err.message); }
  });
}

function statisticsMetrics(summary) {
  return `<div class="progress-grid statistics-metrics">${[
    [summary.total,'решено заданий'],[summary.correct,'верных ответов'],
    [summary.errors,'ошибочных ответов'],[summary.total ? summary.accuracy+'%' : '—','точность']
  ].map(([value,label]) => `<div class="stat"><b>${value}</b><span>${label}</span></div>`).join('')}</div>`;
}

function statisticsActivityTable(data) {
  return `<div class="statistics-table-wrap"><table class="table"><thead><tr><th>Задание / игра</th><th>Решено</th><th>Верно</th><th>Ошибок</th><th>Точность</th><th>Последнее решение</th></tr></thead><tbody>${data.by_activity.map(row => `<tr><td>${escapeHtml(row.title)}</td><td>${row.total}</td><td>${row.correct}</td><td>${row.errors}</td><td>${row.total ? row.accuracy+'%' : '—'}</td><td>${row.last_active ? new Date(row.last_active).toLocaleString('ru-RU') : 'Пока не решал'}</td></tr>`).join('')}</tbody></table></div>`;
}

function statisticsTopics(data) {
  const topics = (rows,empty) => rows.length ? `<ul>${rows.map(row => `<li><b>${escapeHtml(row.activity_title)} · ${escapeHtml(row.rule_name || row.category || '')}</b>: ${row.correct} из ${row.total}, точность ${row.accuracy}%${row.errors ? `, ошибок: ${row.errors}` : ''}</li>`).join('')}</ul>` : `<p class="muted">${empty}</p>`;
  return `<div class="statistics-insights"><section><h3>Сильные стороны</h3><p class="muted">Темы с точностью от 80% после пяти и более ответов.</p>${topics(data.strengths,'Пока недостаточно ответов для уверенной оценки.')}</section><section><h3>На что обратить внимание</h3><p class="muted">До пяти тем с наибольшим количеством ошибок. Все ошибки доступны в журнале ниже.</p>${topics(data.attention,'В выбранном периоде ошибок нет.')}</section></div>`;
}

function statisticsFilters() {
  return `<form class="statistics-period"><label>С даты<input name="from" type="date"></label><label>По дату<input name="to" type="date"></label><button type="submit" class="secondary-button">Применить период</button><button type="button" class="ghost-button" data-period-reset>За всё время</button></form>`;
}

async function showOverallStatistics(updateUrl = true, selectedStudent = '') {
  try { await leaveAssignedWorkspace(); } catch (err) { alert(err.message);return; }
  const request = ++statisticsRequest;
  ++state.activityLoadRequestId;
  stopTeacherStatsRefresh();
  state.currentActivity = null;state.currentSession = null;
  document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
  if (updateUrl) history.pushState(null,'','/apps/statistics');
  renderTopActions();
  const teacher = state.user.role === 'teacher';
  view.innerHTML = `<section class="statistics-page"><div class="panel-head"><div><p class="eyebrow">Все тренажёры и игры</p><h2>${teacher ? 'Общая статистика класса' : 'Моя общая статистика'}</h2></div><button class="secondary-button" data-refresh-statistics>Обновить</button></div>${statisticsFilters()}<p class="muted">Повторные решения учитываются как новые ответы. Ошибки в отдельных словах строки доступны в журнале и не увеличивают количество решённых заданий.</p><div data-statistics-body role="status">Загрузка…</div></section>`;
  window.scrollTo(0,0);
  const page = view.querySelector('.statistics-page');
  const form = page.querySelector('form');
  const period = () => ({...Object.fromEntries([...new FormData(form)].filter(([,v]) => v)),offset_minutes:-new Date().getTimezoneOffset()});
  async function refresh() {
    const body = page.querySelector('[data-statistics-body]');
    body.textContent = 'Загрузка…';
    try {
      const data = await api('/api/statistics?'+new URLSearchParams(period()));
      if (statisticsRequest !== request || !page.isConnected) return;
      body.removeAttribute('role');
      body.innerHTML = statisticsMetrics(data.summary)+(teacher ? `<h3>Ученики (${data.students.length})</h3><label>Найти ученика<input type="search" data-student-search placeholder="Имя ученика"></label><div class="statistics-students">${data.students.map(student => `<details class="statistics-student" data-student-id="${escapeHtml(student.user_id)}"><summary><span><b>${escapeHtml(student.display_name)}</b><small>${student.last_active ? 'Последнее решение: '+new Date(student.last_active).toLocaleString('ru-RU') : 'Пока нет решений'}</small></span><span>${student.total} решений · ${student.total ? student.accuracy+'%' : '—'} · ошибок: ${student.errors}</span></summary><div data-student-body></div></details>`).join('') || '<p>Нет прикреплённых учеников.</p>'}<p data-student-empty class="hidden">Ученики с таким именем не найдены.</p></div><details class="statistics-class"><summary>Общие результаты класса по заданиям и играм</summary>${statisticsActivityTable(data)}</details>` : `<h3>Прогресс по заданиям и играм</h3>${statisticsActivityTable(data)}${statisticsTopics(data)}<h3>История решений и ошибок</h3><div data-own-history></div>`);
      if (teacher) {
        body.querySelector('[data-student-search]').oninput = event => {
          let visible = 0;
          body.querySelectorAll('[data-student-id]').forEach(el => {
            const student = data.students.find(s => s.user_id === el.dataset.studentId);
            el.hidden = !student.display_name.toLocaleLowerCase('ru').includes(event.target.value.toLocaleLowerCase('ru'));
            if (!el.hidden) visible++;
          });
          body.querySelector('[data-student-empty]').classList.toggle('hidden',Boolean(visible));
        };
        body.querySelectorAll('[data-student-id]').forEach(details => {
          details.addEventListener('toggle',async () => {
            if (!details.open || details.dataset.loaded === 'true') return;
            details.dataset.loaded = 'true';
            const target = details.querySelector('[data-student-body]');target.textContent = 'Загрузка…';
            try {
              const filters = {...period(),student_id:details.dataset.studentId};
              const student = await api('/api/statistics?'+new URLSearchParams(filters));
              if (!target.isConnected) return;
              target.innerHTML = `<button class="secondary-button" data-open-student-card="${escapeHtml(details.dataset.studentId)}">Открыть карточку ученика</button>`+statisticsMetrics(student.summary)+`<h4>Прогресс по каждому заданию и игре</h4>`+statisticsActivityTable(student)+statisticsTopics(student)+`<h4>Все решения и ошибки ученика</h4><div data-student-history></div>`;
              mountStatisticsHistory(target.querySelector('[data-student-history]'),student,filters);
            } catch (err) { target.textContent = err.message;details.dataset.loaded = 'false'; }
          });
          if (details.dataset.studentId === selectedStudent) details.open = true;
        });
      } else mountStatisticsHistory(body.querySelector('[data-own-history]'),data,period());
    } catch (err) { if (body.isConnected) body.textContent = err.message; }
  }
  form.onsubmit = event => {event.preventDefault();refresh();};
  form.querySelector('[data-period-reset]').onclick = () => {form.reset();refresh();};
  page.querySelector('[data-refresh-statistics]').onclick = refresh;
  await refresh();
}

function mountStatisticsHistory(root, data, baseFilters) {
  let request = 0,currentPage = 1;
  root.innerHTML = `<form class="statistics-history-filters"><label>Задание или игра<select name="activity"><option value="">Все задания и игры</option><option value="games">Все игры</option>${data.by_activity.map(row => `<option value="${escapeHtml(row.activity)}">${escapeHtml(row.title)}</option>`).join('')}</select></label><label>Ответы<select name="status"><option value="incorrect">Все ошибки</option><option value="all">Все решения</option><option value="correct">Верные ответы</option></select></label><label>Записи<select name="kind"><option value="answers">Только ответы на задания</option><option value="all">Ответы и подробности по словам</option><option value="details">Только подробности по словам</option></select></label><label>Поиск<input name="search" type="search" placeholder="Слово, тема или ответ"></label><button type="submit" class="secondary-button">Показать</button><button type="button" class="ghost-button" data-export-history>Скачать все найденные записи</button></form><p class="muted">Одна ошибка в строке может включать несколько слов. Журнал хранит и ответ на задание, и подробности по словам.</p><div data-history-results role="status"></div><div class="statistics-pagination"><button class="secondary-button" data-history-prev>Предыдущая</button><span data-history-page></span><button class="secondary-button" data-history-next>Следующая</button></div>`;
  const form = root.querySelector('form');
  const filters = () => ({...baseFilters,...Object.fromEntries(new FormData(form))});
  const output = root.querySelector('[data-history-results]');
  const prev = root.querySelector('[data-history-prev]'),next = root.querySelector('[data-history-next]');
  async function load(page) {
    const ticket = ++request;
    prev.disabled = next.disabled = true;output.textContent = 'Загрузка…';
    try {
      const results = await api('/api/statistics/history?'+new URLSearchParams({...filters(),page}));
      if (!root.isConnected || ticket !== request) return;
      currentPage = results.page;
      output.innerHTML = `<p>Найдено записей: <b>${results.total}</b>. Показано ${results.items.length}.</p>`+(results.items.length ? results.items.map(item => `<article class="statistics-answer ${item.is_correct ? 'ok' : 'bad'}"><div class="question-head"><span>${new Date(item.created_at).toLocaleString('ru-RU')} · ${escapeHtml(item.activity_title)}</span><b>${item.detail_kind === 'row_selection' ? 'Подробность выбора строк' : (item.is_detail ? 'Слово · ' : '') + (item.is_correct ? 'Верно' : 'Ошибка')}</b></div><p class="muted">${escapeHtml(item.rule_name || item.category || '')}</p><p class="statistics-prompt">${escapeHtml(item.prompt || 'Текст задания не сохранён')}</p><dl><dt>${escapeHtml(item.exercise_correct_answer ? 'Ответ ученика (номера строк)' : item.answer_label || 'Ответ ученика')}</dt><dd>${escapeHtml(item.exercise_given_answer || item.given_answer || 'Не сохранён')}</dd><dt>${escapeHtml(item.exercise_correct_answer ? 'Правильный ответ (номера строк)' : item.correct_answer_label || 'Правильный ответ')}</dt><dd>${escapeHtml(item.exercise_correct_answer || item.correct_answer || 'Не сохранён')}</dd>${item.word_correct_answer ? `<dt>Буква в этом слове</dt><dd>${escapeHtml(item.word_correct_answer)}</dd>` : ''}</dl>${item.answer_note ? `<p class="muted">${escapeHtml(item.answer_note)}</p>` : ''}${renderLetterResults(item.letter_results)}${item.correct_spelling ? `<p>${escapeHtml(item.correct_spelling)}</p>` : ''}${item.explanation ? `<details><summary>Объяснение</summary><p>${escapeHtml(item.explanation)}</p></details>` : ''}${!item.is_correct && item.can_repeat ? `<button class="secondary-button" data-repeat-error="${escapeHtml(item.attempt_id)}">${state.user.role === 'teacher' ? 'Назначить повторение ошибки' : 'Повторить ошибку'}</button>` : !item.is_correct && item.repeat_game_url ? `<a class="secondary-button" href="${escapeHtml(item.repeat_game_url)}">Повторить в игре</a>` : ''}${!item.content_available ? '<p class="muted">В этой записи не сохранены подробности ответа. Восстановить полный разбор по ней невозможно.</p>' : ''}</article>`).join('') : '<p>По выбранным фильтрам записей нет.</p>');
      root.querySelector('[data-history-page]').textContent = `Страница ${results.page} из ${results.pages}`;
      prev.disabled = currentPage === 1;next.disabled = currentPage === results.pages;
    } catch (err) { if (output.isConnected && ticket === request) output.textContent = err.message; }
  }
  form.onsubmit = event => {event.preventDefault();load(1);};
  prev.onclick = () => load(currentPage-1);next.onclick = () => load(currentPage+1);
  root.querySelector('[data-export-history]').onclick = () => downloadRequest('/api/statistics/export?'+new URLSearchParams(filters()),'statistics.csv').catch(err => alert(err.message));
  load(1);
}
